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
