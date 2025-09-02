# -*- coding: utf-8 -*-
from datetime import date
import time
from typing import Any
import unittest

import django

from core.banking import (
    cents_to_euros,
    extract_bank_ref,
    format_bank_id,
    generate_payment_QR_code_content,
    import_bank_statements,
    make_payment_builder,
    normalize_bank_id,
    parse_date_received,
)
from core.models import Payment

YEAR_PREFIX = time.strftime("%Y")


class FormatBankId(unittest.TestCase):
    def test_with_valid_bank_id(self):
        self.assertEqual(format_bank_id('123456789012'), '+++123/4567/89012+++')
        self.assertEqual(format_bank_id(format_bank_id('123456789012')), '+++123/4567/89012+++')

    def test_with_invalid_bank_id(self):
        self.assertEqual(format_bank_id('invalid'), 'invalid')


class NormalizeBankId(unittest.TestCase):
    def test_with_valid_bank_id(self):
        self.assertEqual(normalize_bank_id('123456789012'), '123456789012')
        self.assertEqual(normalize_bank_id(format_bank_id('123456654321')), '123456654321')
        self.assertEqual(normalize_bank_id('+++123/1234/12345+++'), '123123412345')

    def test_with_invalid_bank_id(self):
        self.assertEqual(normalize_bank_id('invalid'), '')
        self.assertEqual(normalize_bank_id('12341234123412341234'), '')
        self.assertEqual(normalize_bank_id(''), '')




class CentsToEuro(unittest.TestCase):
    def test_examples(self):
        for (cents, expected) in [(100, '1.00'), (123, '1.23'), (20, '0.20'), (3, '0.03'), (3001, '30.01'),
                                  (-1, '-0.01'), (-19, '-0.19'), (-99, '-0.99'), (-12345, '-123.45')]:
            with self.subTest(cents=cents, expected=expected, unit=''):
                self.assertEqual(cents_to_euros(cents, unit=''), expected)
        with self.subTest(unit='$'):
            self.assertEqual(cents_to_euros(123, unit='$'), '1.23$')
        with self.subTest(unit=None):
            self.assertEqual(cents_to_euros(123), '1.23€')


class GeneratePaymentQRCodeContent(unittest.TestCase):
    def test_generate_payment_QR_code_content(self):
        self.assertEqual(
            generate_payment_QR_code_content(
                12045, # cents, i.e. 120.45€
                "483513812577",
                organizer_name="Music and Food",
                organizer_bic="GABBBEBB",
                bank_account="BE89 3751 0478 0085"),
            "BCD\n001\n1\nSCT\nGABBBEBB\nMusic and Food\nBE89375104780085\nEUR120.45\n\n483513812577",
        )


class ExtractBankRef(unittest.TestCase):
    def test_example(self):
        self.assertEqual(extract_bank_ref('VIREMENT EN EUROS DU COMPTE BE00020002000202 BIC GABBBEBB CCCCC-CCCCCCCCC AV DE LA GARE 76 9999 WAGADOUGOU COMMUNICATION : REPRISE MARCHANDISES (VIANDE HACHEE) SOUPER ITALIEN REFERENCE BANQUE : 23032412000 DATE VALEUR : 28/03/2023'), '23032412000')

    def test_raises_when_no_left_marker(self):
        self.assertRaises(ValueError, extract_bank_ref, 'Tralala')

    def test_raises_when_no_right_marker(self):
        self.assertRaises(ValueError, extract_bank_ref, 'DATE VALEUR : 28/03/2023 SOUPER ITALIEN REFERENCE BANQUE : 23032412000 Trululu')



class ParseDateReceived(unittest.TestCase):
    def test_european_forma(self) -> None:
        self.assertEqual(parse_date_received('28/03/2023'), date(2023, 3, 28))
    def test_iso_format(self) -> None:
        self.assertEqual(parse_date_received('2025-02-12'), date(2025, 2, 12))


class MakePaymentBuilder(unittest.TestCase):
    EXAMPLE_DATA = [
        ['Nº de séquence', "Date d'exécution", 'Date valeur', 'Montant', 'Devise du compte', 'Numéro de compte', 'Type de transaction', 'Contrepartie', 'Nom de la contrepartie', 'Communication', 'Détails', 'Statut', 'Motif du refus'],
        [f'{YEAR_PREFIX}-00127', '28/03/2023', '28/03/2023', '18', 'EUR', 'BE00010001000101', 'Virement en euros', 'BE00020002000202', 'ccccc-ccccccccc', 'Reprise marchandises (viande hachee) souper italien', 'VIREMENT EN EUROS DU COMPTE BE00020002000202 BIC GABBBEBB CCCCC-CCCCCCCCC AV DE LA GARE 76 9999 WAGADOUGOU COMMUNICATION : REPRISE MARCHANDISES (VIANDE HACHEE) SOUPER ITALIEN REFERENCE BANQUE : 23032412000 DATE VALEUR : 28/03/2023', 'Accepté', ''],
        [f'{YEAR_PREFIX}-00126', '26/02/2023', '26/02/2023', '-50.34', 'EUR', 'BE00010001000101', 'Virement en euros', 'BE00030003000303', 'HHHHHHH SSSSSSSS', '+++671/4235/58049+++', 'VIREMENT EN EUROS DU COMPTE BE00030003000303 BIC GABBBEBB HHHHHHH SSSSSSSS CHEMIN DE LA GARE 123 9999 WAGADOUGOU COMMUNICATION : COTISATION REFERENCE BANQUE : 23032409001 DATE VALEUR : 26/02/2023', 'Accepté', ''],
    ]
    def test_examples(self):
        def to_dict(pmnt: Payment) -> dict[str, Any]:
            return {
                'date_received': pmnt.date_received,
                'amount_in_cents': pmnt.amount_in_cents,
                'comment': pmnt.comment,
                'src_id': pmnt.src_id,
                'bank_ref': pmnt.bank_ref,
                'other_account': pmnt.other_account,
                'other_name': pmnt.other_name,
                'srh_bank_id': pmnt.srh_bank_id,
                'status': pmnt.status,
                'active': pmnt.active,
            }

        def sub_test(data_row: int, byte_order_mark: str, expected_dict: dict[str, Any]) -> None:
            builder = make_payment_builder(
                [byte_order_mark + self.EXAMPLE_DATA[0][0]] + self.EXAMPLE_DATA[0][1:])
            with self.subTest(data_row=data_row, byte_order_mark=byte_order_mark):
                self.assertEqual(
                    to_dict(builder(self.EXAMPLE_DATA[data_row + 1])), expected_dict)

        sub_test(0, '', {
            'date_received': date(2023, 3, 28),
            'amount_in_cents': 1800,
            'comment': 'Reprise marchandises (viande hachee) souper italien',
            'src_id': f'{YEAR_PREFIX}-00127',
            'bank_ref': '23032412000',
            'other_account': 'BE00020002000202',
            'other_name': 'ccccc-ccccccccc',
            'srh_bank_id': '',
            'status': 'Accepté',
            'active': True})
        sub_test(0, '\ufeff', {
            'date_received': date(2023, 3, 28),
            'amount_in_cents': 1800,
            'comment': 'Reprise marchandises (viande hachee) souper italien',
            'src_id': f'{YEAR_PREFIX}-00127',
            'bank_ref': '23032412000',
            'other_account': 'BE00020002000202',
            'other_name': 'ccccc-ccccccccc',
            'srh_bank_id': '',
            'status': 'Accepté',
            'active': True})
        sub_test(1, '', {
            'date_received': date(2023, 2, 26),
            'amount_in_cents': -5034,
            'comment': '+++671/4235/58049+++',
            'src_id': f'{YEAR_PREFIX}-00126',
            'bank_ref': '23032409001',
            'other_account': 'BE00030003000303',
            'other_name': 'HHHHHHH SSSSSSSS',
            'srh_bank_id': '671423558049',
            'status': 'Accepté',
            'active': True})


class ImportBankStatements(django.test.TransactionTestCase):
    bank_statements_csv = [
        "Nº de séquence;Date d'exécution;Date valeur;Montant;Devise du compte;Numéro de compte;Type de transaction;Contrepartie;Nom de la contrepartie;Communication;Détails;Statut;Motif du refus",
        f"{YEAR_PREFIX}-00127;28/03/{YEAR_PREFIX};28/03/{YEAR_PREFIX};18;EUR;BE00010001000101;Virement en euros;BE00020002000202;ccccc-ccccccccc;Reprise marchandises (viande hachee) souper italien;VIREMENT EN EUROS DU COMPTE BE00020002000202 BIC GABBBEBB CCCCC-CCCCCCCCC AV DE LA GARE 76 9999 WAGADOUGOU COMMUNICATION : REPRISE MARCHANDISES (VIANDE HACHEE) SOUPER ITALIEN REFERENCE BANQUE : {YEAR_PREFIX[2:4]}032412002 DATE VALEUR : 28/03/{YEAR_PREFIX};Accepté;",
        f"{YEAR_PREFIX}-00126;28/03/{YEAR_PREFIX};28/03/{YEAR_PREFIX};50;EUR;BE00010001000101;Virement en euros;BE00030003000303;HHHHHHH SSSSSSSS;Cotisation;VIREMENT EN EUROS DU COMPTE BE00030003000303 BIC GABBBEBB HHHHHHH SSSSSSSS CHEMIN DE LA GARE 123 9999 WAGADOUGOU COMMUNICATION : COTISATION REFERENCE BANQUE : {YEAR_PREFIX[2:4]}032409003 DATE VALEUR : 28/03/{YEAR_PREFIX};Accepté;",
        f"{YEAR_PREFIX}-00125;28/03/{YEAR_PREFIX};28/03/{YEAR_PREFIX};54;EUR;BE00010001000101;Virement en euros;BE00040004000404;Mme RRRRRRRRRR GGGGG;Souper italien du 25/03 : 2 x 27;VIREMENT EN EUROS DU COMPTE BE00 0400 0400 0404 BIC GABBBEBB MME RRRRRRRRRR GGGGG RUE DE LA GARE,3 3333 ZANZIBAR COMMUNICATION : SOUPER ITALIEN DU 25/03 : 2 X 27 REFERENCE BANQUE : {YEAR_PREFIX[2:4]}032406004 DATE VALEUR : 28/03/{YEAR_PREFIX};Accepté",
        f"{YEAR_PREFIX}-00124;27/03/{YEAR_PREFIX};27/03/{YEAR_PREFIX};-54;EUR;BE00010001000101;Virement en euros;BE00050005000505;Aaa Bbbbbbbb;Remboursement repas italien Harmonie ( pas venu);VIREMENT EN EUROS AU COMPTE BE00 0500 0500 0505 BIC GABBBEBB VIA MOBILE BANKING AAA BBBBBBBB COMMUNICATION : REMBOURSEMENT REPAS ITALIEN HARMONIE ( PAS VENU) BISES ANDRE REFERENCE BANQUE : {YEAR_PREFIX[2:4]}032430005 DATE VALEUR : 27/03/{YEAR_PREFIX};Accepté;",
        f"{YEAR_PREFIX}-00123;27/03/{YEAR_PREFIX};27/03/{YEAR_PREFIX};15;EUR;BE00010001000101;Paiement par carte;BE060006000606;BANKSYS;068962070000270121363927012136391010271908660328072700000620700000000088000000000000000P2P MOBILE 000;PAIEMENT MOBILE COMPTE DU DONNEUR D'ORDRE : BE06 0006 0006 06 BIC GABBBEBB BANCONTACT REFERENCE BANQUE : {YEAR_PREFIX[2:4]}032427006 DATE VALEUR : 27/03/{YEAR_PREFIX};Accepté;",
        f"{YEAR_PREFIX}-00122;27/03/{YEAR_PREFIX};27/03/{YEAR_PREFIX};57;EUR;BE00010001000101;Virement en euros;BE070007000707;OOOOO QQQQQ;;VIREMENT EN EUROS DU COMPTE BE07 0007 0007 07 BIC GABBBEBB OOOOO QQQQQ CHAUSSEE DE LA GARE 5 1440 6666 PORT-AU-BOUC PAS DE COMMUNICATION REFERENCE BANQUE : {YEAR_PREFIX[2:4]}032424007 DATE VALEUR : 27/03/{YEAR_PREFIX};Accepté;",
        f"{YEAR_PREFIX}-00121;27/03/{YEAR_PREFIX};27/03/{YEAR_PREFIX};60;EUR;BE00010001000101;Virement instantané en euros;BE080008000808;EEEEEEE JJJJJJ;Cotisation Eeeeeee - Jjjjjj;VIREMENT INSTANTANE EN EUROS BE08 0008 0008 08 BIC GABBBEBBXXX EEEEEEE JJJJJJ RUE DE LA MARIEE 50 7777 NEW YORK COMMUNICATION : COTISATION EEEEEEE - JJJJJJ REFERENCE BANQUE : {YEAR_PREFIX[2:4]}032448008 DATE VALEUR : 27/03/{YEAR_PREFIX};Accepté;",
        f"{YEAR_PREFIX}-00120;26/03/{YEAR_PREFIX};26/03/{YEAR_PREFIX};25;EUR;BE00010001000101;Virement instantané en euros;BE090009000909;DDDDDDD VVVVVVVVVVVVVVVVV;Llll Aaaa cotisation;VIREMENT INSTANTANE EN EUROS BE09 0009 0009 09 BIC GABBBEBBXXX DDDDDDD VVVVVVVVVVVVVVVVV RUE DES MIETTES 32 6666 HYDERABAD COMMUNICATION : LLLL AAAA COTISATION REFERENCE BANQUE : {YEAR_PREFIX[2:4]}032445009 DATE VALEUR : 26/03/{YEAR_PREFIX};Accepté;",
        f"{YEAR_PREFIX}-00119;25/03/{YEAR_PREFIX};24/03/{YEAR_PREFIX};27;EUR;BE00010001000101;Virement instantané en euros;BE100010001010;SSSSSS GGGGGGGG;+++671/4235/58049+++;VIREMENT INSTANTANE EN EUROS BE10 0010 0010 10 BIC GABBBEBBXXX SSSSSS GGGGGGGG RUE MARIGNON 43/5 8888 BANDARLOG COMMUNICATION : 671423558049 EXECUTE LE 24/03 REFERENCE BANQUE : {YEAR_PREFIX[2:4]}032442010 DATE VALEUR : 24/03/{YEAR_PREFIX};Accepté;",
        f"{YEAR_PREFIX}-00118;24/03/{YEAR_PREFIX};23/03/{YEAR_PREFIX};16;EUR;BE00010001000101;Virement en euros;BE110011001111;WWWWWWW XXXXXXXX;+++402/9754/33613+++;VIREMENT EN EUROS DU COMPTE BE11 0011 0011 11 BIC GABBBEBB WWWWWWW XXXXXXXX CLOS DE LA GARE 30 8888 BANDARLOG COMMUNICATION : 402975433613 REFERENCE BANQUE : {YEAR_PREFIX[2:4]}032439011 DATE VALEUR : 23/03/{YEAR_PREFIX};Accepté;",
        f"{YEAR_PREFIX}-00117;24/03/{YEAR_PREFIX};24/03/{YEAR_PREFIX};81;EUR;BE00010001000101;Virement en euros;BE202020202020;JAJAJA-BLBLBLBL;+++483/5138/12577+++;VIREMENT EN EUROS DU COMPTE BE20 0013 0492 7256 BIC GABBBEBB JAJAJA-BLBLBLBL AV. DE L'EGLISE 41 8888 BANDARLOG COMMUNICATION : 483513812577 REFERENCE BANQUE : {YEAR_PREFIX[2:4]}032463012 DATE VALEUR : 24/03/{YEAR_PREFIX};Accepté;",
        f"{YEAR_PREFIX}-00116;23/03/{YEAR_PREFIX};23/03/{YEAR_PREFIX};-33.6;EUR;BE00010001000101;Paiement par carte;;;;PAIEMENT AVEC LA CARTE DE DEBIT NUMERO 4871 09XX XXXX 7079 GROENDEKOR BVBA SINT-PIET 23/03/2023 BANCONTACT REFERENCE BANQUE : {YEAR_PREFIX[2:4]}032460013 DATE VALEUR : 23/03/{YEAR_PREFIX};Accepté;",
        f"{YEAR_PREFIX}-00115;23/03/{YEAR_PREFIX};22/03/{YEAR_PREFIX};16;EUR;BE00010001000101;Virement en euros;BE110011001111;WWWWWWW XXXXXXXX;+++476/7706/09825+++;VIREMENT EN EUROS DU COMPTE BE11 0011 0011 11 BIC GABBBEBB WWWWWWW XXXXXXXX CLOS DE LA GARE 30 8888 BANDARLOG COMMUNICATION : 476770609825 REFERENCE BANQUE : {YEAR_PREFIX[2:4]}032457014 DATE VALEUR : 22/03/{YEAR_PREFIX};Accepté;",
        f"{YEAR_PREFIX}-00114;23/03/{YEAR_PREFIX};23/03/{YEAR_PREFIX};54;EUR;BE00010001000101;Virement en euros;BE120012001212;Ggggggggggg Gggggg;852598350718;VIREMENT EN EUROS DU COMPTE BE12 0012 0012 12 BIC GABBBEBB GGGGGGGGGGG GGGGGG PLACE DE LA GARE 12 8888 BANDARLOG COMMUNICATION : 852598350718 REFERENCE BANQUE : {YEAR_PREFIX[2:4]}032454015 DATE VALEUR : 23/03/{YEAR_PREFIX};Accepté;",
        f"{YEAR_PREFIX}-00113;22/03/{YEAR_PREFIX};22/03/{YEAR_PREFIX};-100.87;EUR;BE00010001000101;Virement en euros;BE89375104780085;Unisono;+++323/0086/13607+++;VIREMENT EN EUROS AU COMPTE BE89 3751 0478 0085 BIC GABBBEBB VIA MOBILE BANKING UNISONO COMMUNICATION : 323008613607 REFERENCE BANQUE : {YEAR_PREFIX[2:4]}032478016 DATE VALEUR : 22/03/{YEAR_PREFIX};Accepté;",
        f"{YEAR_PREFIX}-00112;22/03/{YEAR_PREFIX};21/03/{YEAR_PREFIX};25;EUR;BE00010001000101;Virement en euros;BE130013001313;DEDEDEDE DEDED;Cotisation SRH;VIREMENT EN EUROS DU COMPTE BE13 0013 0013 13 BIC GABBBEBB DEDEDEDE DEDED RUE DE L'EGLISE 33 6666 PORT-AU-BOUC COMMUNICATION : COTISATION SRH REFERENCE BANQUE : {YEAR_PREFIX[2:4]}032475017 DATE VALEUR : 21/03/{YEAR_PREFIX};Accepté;",
        f"{YEAR_PREFIX}-00111;22/03/{YEAR_PREFIX};22/03/{YEAR_PREFIX};27;EUR;BE00010001000101;Virement en euros;BE140014001414;SOSOSOS OSOSOS;+++409/5503/55816+++;VIREMENT EN EUROS DU COMPTE BE14 0014 0014 14 BIC GABBBEBB SOSOSOS OSOSOS RUE DES APACHES 42 5555 ZOLLIKON COMMUNICATION : 409550355816 REFERENCE BANQUE : {YEAR_PREFIX[2:4]}032472018 DATE VALEUR : 22/03/{YEAR_PREFIX};Accepté;",
        f"{YEAR_PREFIX}-00110;22/03/{YEAR_PREFIX};22/03/{YEAR_PREFIX};54;EUR;BE00010001000101;Virement en euros;BE150015001515;Iaiaiaiaia Iaia;483421245780;VIREMENT EN EUROS DU COMPTE BE15 0015 0015 15 BIC GABBBEBB IAIAIAIAIA IAIA BOULEVARD DE LA GARE 67 4444 MODANE COMMUNICATION : 483421245780 REFERENCE BANQUE : {YEAR_PREFIX[2:4]}032496019 DATE VALEUR : 22/03/{YEAR_PREFIX};Accepté;",
        f";21/03/{YEAR_PREFIX};21/03/{YEAR_PREFIX};81;EUR;BE00010001000101;Virement en euros;BE160016001616;SCSCSCSC-XSXSXSXS;+++409/6346/26382+++;VIREMENT EN EUROS DU COMPTE BE16 0016 0016 16 BIC GABBBEBB SCSCSCSC-XSXSXSXS RUE DU PORT 23 8888 BANDARLOG COMMUNICATION : 409634626382 REFERENCE BANQUE : {YEAR_PREFIX[2:4]}032493020 DATE VALEUR : 21/03/{YEAR_PREFIX};Accepté;",
        f";21/03/{YEAR_PREFIX};21/03/{YEAR_PREFIX};108;EUR;BE00010001000101;Virement en euros;BE170017001717;BOBOBO BOBOBO;+++389/5147/28354+++;VIREMENT EN EUROS DU COMPTE BE17 0017 0017 17 BIC GABBBEBB BOBOBO BOBOBO CLOS DE LA COLLINE 13 8888 BANDARLOG COMMUNICATION : 389514728354 REFERENCE BANQUE : {YEAR_PREFIX[2:4]}032490021 DATE VALEUR : 21/03/{YEAR_PREFIX};Accepté;",
        f"{YEAR_PREFIX}-;21/03/{YEAR_PREFIX};21/03/{YEAR_PREFIX};108;EUR;BE00010001000101;Virement en euros;BE180018001818;BABABA BABABA;147018018095;VIREMENT EN EUROS DU COMPTE BE18 0018 0018 18 BIC GABBBEBB BABABA BABABA SQUARE DE LA VALLEE 18 8888 BANDARLOG COMMUNICATION : 147018018095 REFERENCE BANQUE : {YEAR_PREFIX[2:4]}032490180 DATE VALEUR : 21/03/{YEAR_PREFIX};Accepté;",
    ]

    def test_non_overlapping_uploads(self):
        initial_count = Payment.objects.count()
        first_batch = self.bank_statements_csv[:len(self.bank_statements_csv) // 2]
        assert len(first_batch) > 1, "Pre-condition not met: not enough test data for 1st batch"
        second_batch = [self.bank_statements_csv[0]] + self.bank_statements_csv[len(first_batch):]
        assert len(second_batch) > 1, "Pre-condition not met: not enough test data for 2nd batch"

        first_import = import_bank_statements(first_batch)
        self.assertEqual(len(first_import), len(first_batch) - 1)
        self.maxDiff = None
        self.assertEqual(list(exc for exc, _ in first_import), [None] * len(first_import))
        self.assertEqual(Payment.objects.count() - initial_count, len(first_batch) - 1)

        second_import = import_bank_statements(second_batch)
        self.assertEqual(len(second_import), len(second_batch) - 1)
        self.assertTrue(all(exc is None for exc, _ in second_import))
        self.assertEqual(Payment.objects.count() - initial_count, len(self.bank_statements_csv) - 1)

        third_import = import_bank_statements(
            [self.bank_statements_csv[0]] + [
                f"{YEAR_PREFIX}-00108;21/03/{YEAR_PREFIX};21/03/{YEAR_PREFIX};108;EUR;BE00010001000101;Virement en euros;BE170017001717;BOBOBO BOBOBO;+++389/5147/28354+++;VIREMENT EN EUROS DU COMPTE BE17 0017 0017 17 BIC GABBBEBB BOBOBO BOBOBO CLOS DE LA COLLINE 13 8888 BANDARLOG COMMUNICATION : 389514728354 REFERENCE BANQUE : {YEAR_PREFIX[2:4]}032490021 DATE VALEUR : 21/03/{YEAR_PREFIX};Accepté;",
                f"{YEAR_PREFIX}-00109;21/03/{YEAR_PREFIX};21/03/{YEAR_PREFIX};81;EUR;BE00010001000101;Virement en euros;BE160016001616;SCSCSCSC-XSXSXSXS;change in comment will cause this to fail;VIREMENT EN EUROS DU COMPTE BE16 0016 0016 16 BIC GABBBEBB SCSCSCSC-XSXSXSXS RUE DU PORT 23 8888 BANDARLOG COMMUNICATION : 409634626382 REFERENCE BANQUE : {YEAR_PREFIX[2:4]}032493020 DATE VALEUR : 21/03/{YEAR_PREFIX};Accepté;",
                f"{YEAR_PREFIX}-00999;21/03/{YEAR_PREFIX};21/03/{YEAR_PREFIX};81;EUR;BE00010001000101;Virement en euros;BE160016001616;SCSCSCSC-XSXSXSXS;+++409/6346/26382+++;VIREMENT EN EUROS DU COMPTE BE16 0016 0016 16 BIC GABBBEBB SCSCSCSC-XSXSXSXS RUE DU PORT 23 8888 BANDARLOG COMMUNICATION : 409634626382 REFERENCE BANQUE : {YEAR_PREFIX[2:4]}032493020 DATE VALEUR : 21/03/{YEAR_PREFIX};Accepté;",
                # src_id with special format like "2024-" (no trailing numbers) get updated once
                f"{YEAR_PREFIX}-00998;21/03/{YEAR_PREFIX};21/03/{YEAR_PREFIX};108;EUR;BE00010001000101;Virement en euros;BE180018001818;BABABA BABABA;147018018095;VIREMENT EN EUROS DU COMPTE BE18 0018 0018 18 BIC GABBBEBB BABABA BABABA SQUARE DE LA VALLEE 18 8888 BANDARLOG COMMUNICATION : 147018018095 REFERENCE BANQUE : {YEAR_PREFIX[2:4]}032490180 DATE VALEUR : 21/03/{YEAR_PREFIX};Accepté;",
                # but src_id will not be updated a second time
                f"{YEAR_PREFIX}-99900;21/03/{YEAR_PREFIX};21/03/{YEAR_PREFIX};81;EUR;BE00010001000101;Virement en euros;BE160016001616;SCSCSCSC-XSXSXSXS;+++409/6346/26382+++;VIREMENT EN EUROS DU COMPTE BE16 0016 0016 16 BIC GABBBEBB SCSCSCSC-XSXSXSXS RUE DU PORT 23 8888 BANDARLOG COMMUNICATION : 409634626382 REFERENCE BANQUE : {YEAR_PREFIX[2:4]}032493020 DATE VALEUR : 21/03/{YEAR_PREFIX};Accepté;",
                # src_id with special format like "2024-" (no trailing numbers) get updated once but not twice
                f"{YEAR_PREFIX}-99901;21/03/{YEAR_PREFIX};21/03/{YEAR_PREFIX};108;EUR;BE00010001000101;Virement en euros;BE180018001818;BABABA BABABA;147018018095;VIREMENT EN EUROS DU COMPTE BE18 0018 0018 18 BIC GABBBEBB BABABA BABABA SQUARE DE LA VALLEE 18 8888 BANDARLOG COMMUNICATION : 147018018095 REFERENCE BANQUE : {YEAR_PREFIX[2:4]}032490180 DATE VALEUR : 21/03/{YEAR_PREFIX};Accepté;"])
        self.assertEqual(len(third_import), 6)
        self.assertIsNone(third_import[0][0])
        self.assertIsNotNone(third_import[1][0])
        self.assertIsNone(third_import[2][0])
        self.assertIsNone(third_import[3][0])
        self.assertIsNotNone(third_import[4][0])
        self.assertIsNotNone(third_import[5][0])
        self.assertEqual(
            Payment.find_by_bank_ref(third_import[-2][-1].bank_ref).src_id, f"{YEAR_PREFIX}-00999"
        )
        self.assertEqual(
            Payment.find_by_bank_ref(third_import[-1][-1].bank_ref).src_id, f"{YEAR_PREFIX}-00998"
        )
        self.assertEqual(Payment.objects.count() - initial_count, len(self.bank_statements_csv) - 1)
 
    def test_overlapping_uploads(self):
        initial_count = Payment.objects.count()
        first_batch = self.bank_statements_csv[:6]
        assert len(first_batch) > 1, "Pre-condition not met: not enough test data for 1st batch"
        second_batch = [self.bank_statements_csv[0]] + self.bank_statements_csv[4:]
        assert len(second_batch) > 1, "Pre-condition not met: not enough test data for 2nd batch"
        import_bank_statements(first_batch)
        self.assertEqual(Payment.objects.count() - initial_count, len(first_batch) - 1)

        import_bank_statements(second_batch)
        self.assertEqual(Payment.objects.count() - initial_count, len(self.bank_statements_csv) - 1)

# Local Variables:
# compile-command: "uv run python ../../manage.py test core"
# End:
