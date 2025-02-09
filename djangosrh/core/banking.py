import csv
from datetime import date
import io
import time
from typing import Callable, Iterable

from django.db import IntegrityError

from core.models import Payment


def cents_to_euros(display_value: str|int, unit: str="€") -> str:
    try:
        value = int(display_value)
        euros = abs(value) // 100
        cents = abs(value) % 100
        sign = "" if value >= 0 else "-"
        return f"{sign}{euros}.{cents:02d}{unit}"
    except (TypeError, ValueError):
        return ""


def generate_payment_QR_code_content(remaining_due: int, bank_id: str, bank_account: str, organizer_bic: str, organizer_name: str) -> str:
    # See https://scan2pay.info
    iban = "".join(ch for ch in bank_account if ch in "BE" or ch.isdigit())
    amount = cents_to_euros(remaining_due, unit="")
    return ("BCD\n001\n1\nSCT\n" + organizer_bic + "\n" + organizer_name + "\n" + iban + "\n" + "EUR" + amount + "\n\n" + bank_id)


def generate_bank_id(time_time: float, number_of_previous_calls: int) -> str:
    data = [(x & ((1 << b) - 1), b)
            for (x, b)
            in ((round(time_time * 100.0), 24),
                (number_of_previous_calls, 9))]
    n = 0
    for (x, b) in data:
        n = (n << b) + x
    s = f'{n:010}'
    n = 0
    for c in s:
        n = (n * 10 + int(c)) % 97
    if n == 0:
        n = 97
    return f'{s}{n:02}'


def format_bank_id(x: str) -> str:
    bank_id = ''.join(c for c in x if c.isdigit())
    if len(bank_id) != 12:
        return x
    return f'+++{bank_id[0:3]}/{bank_id[3:7]}/{bank_id[7:12]}+++'


def normalize_bank_id(x: str) -> str:
    if len(x) == 12 and all(c.isdigit() for c in x):
        return x
    if x.startswith('+++') and x.endswith('+++') and len(x) == 20:
        return normalize_bank_id(x[3:6] + x[7:11] + x[12:17])
    return ''


def extract_bank_ref(details: str) -> str:
    left_marker = "REFERENCE BANQUE :"
    right_marker = "DATE VALEUR"
    left_idx = details.find(left_marker)
    if left_idx < 0:
        raise ValueError(f"{left_marker!r} not found in {details!r}")
    left_idx += len(left_marker)
    right_idx = details.find(right_marker, left_idx)
    if right_idx < left_idx:
        raise ValueError(f"{left_marker!r} not found in {details[left_idx:]!r}")
    return details[left_idx:right_idx].strip()


def parse_date_received(date_rcv: str) -> date:
    try:
        return date.fromisoformat(date_rcv)
    except ValueError:
        try:
            dd, mm, yyyy = date_rcv.split('/')
            return date(int(yyyy), int(mm), int(dd))
        except Exception:
            raise ValueError(f"Unable to parse {date_rcv!r} as a date")


def make_payment_builder(header_row: list[str]) -> Callable[[list[str]], Payment]:
    BANK_STATEMENT_HEADERS = {
        "fr": {'N\xba de s\xe9quence': "src_id",
               'Date d\'ex\xe9cution': "timestamp",
               'Montant': "amount_in_cents",
               'Contrepartie': "other_account",
               'Nom de la contrepartie': "other_name",
               'Statut': "status",
               'Détails': "details",
               'Communication': "comment"}}

    def _normalize_header(s: str) -> str:
        s = s.strip()
        return s[1:] if s.startswith('\ufeff') else s


    col_name_to_idx = {_normalize_header(col_name): col_idx for col_idx, col_name in enumerate(header_row)}
    columns = {}
    for mapping in BANK_STATEMENT_HEADERS.values():
        try:
            columns = {attr_name: col_name_to_idx[col_name] for col_name, attr_name in mapping.items()}
        except KeyError:
            pass
    if not columns:
        raise RuntimeError("Unable to map header row to Payment class definition")

    def payment_builder(row: list[str]) -> Payment:
        amount_in_cents = round(float(row[columns["amount_in_cents"]].replace(",", ".")) * 100)
        comment = row[columns['comment']]
        return Payment(
            date_received=parse_date_received(row[columns['timestamp']]),
            amount_in_cents=amount_in_cents,
            comment=comment,
            src_id=row[columns['src_id']],
            bank_ref=extract_bank_ref(row[columns['details']]),
            other_account=row[columns['other_account']],
            other_name=row[columns['other_name']],
            srh_bank_id=normalize_bank_id(comment),
            status=row[columns['status']],
            active=True,
        )

    return payment_builder
        

def is_blank_src_id(src_id: str | None) -> bool:
    """True if src_id is blank or <<incomplete as observed in our bank statements>>

    Some bank records have a src_id=='2024-' that gets updated during a later import,
    let's count these as empty, too."""
    return not src_id or not src_id.strip() or (src_id.endswith('-') and all(ch.isdigit() for ch in src_id[:-1]))


def import_bank_statements(bank_statements_csv: Iterable[str]) -> list[tuple[Exception | None, Payment]]:
    """Parse bank statements CSV and insert/update the rows in the database

    For each row, a tuple is returned: the second element is the record parsed
    from the CSV, the first element is None if the row caused a change in the
    DB or the exception that prevented the DB update otherwise.

    Normally, rows are only inserted, not updated with one exception: the bank
    sometimes exports rows in the CSV without a valid src_id (valid would be
    e.g. 2024-00123) and later imports will contain the same row except with a
    `corrected' src_id.  In this case, the row is updated in the DB to reflect the
    valid src_id issued by the bank."""
    csv_reader = csv.reader(bank_statements_csv, delimiter=';')
    builder = make_payment_builder(next(csv_reader))
    exceptions: list[tuple[Exception | None, Payment]] = []
    src_id_limit = time.strftime("%Y-")
    for row in csv_reader:
        pmnt = builder(row)
        if not is_blank_src_id(pmnt.src_id) and pmnt.src_id < src_id_limit:
            exceptions.append((RuntimeError(f"Bank statement {pmnt.src_id!r} is too old"), pmnt))
            continue
        try:
            # update src_id if it did not exist yet
            if (pre_existing := Payment.find_by_bank_ref(pmnt.bank_ref)
                ) and is_blank_src_id(pre_existing.src_id) :
                columns_to_compare = ("amount_in_cents", "comment", "bank_ref", "other_account", "other_name")
                pre_dict = {key: getattr(pre_existing, key) for key in columns_to_compare}
                new_dict = {key: getattr(pmnt, key) for key in columns_to_compare}
                if pre_dict == new_dict:
                    try:
                        pre_existing.src_id = pmnt.src_id
                        pre_existing.save()
                    except Exception as fyd:
                        exceptions.append((fyd, pmnt))
                    else:
                        exceptions.append((None, pmnt))
                else:
                    exceptions.append((Exception("Duplicate bank_ref for different statements"), pmnt))
                continue
            else:
                pmnt.save()
        except Exception as exc:
            exceptions.append((exc, pmnt))
        else:
            exceptions.append((None, pmnt))
    return exceptions
