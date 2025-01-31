# -*- coding: utf-8 -*-
import unittest

from core.banking import cents_to_euros, format_bank_id, generate_payment_QR_code_content

class FormatBankId(unittest.TestCase):
    def test_with_valid_bank_id(self):
        self.assertEqual(format_bank_id('123456789012'), '+++123/4567/89012+++')
        self.assertEqual(format_bank_id(format_bank_id('123456789012')), '+++123/4567/89012+++')

    def test_with_invalid_bank_id(self):
        self.assertEqual(format_bank_id('invalid'), 'invalid')


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


# Local Variables:
# compile-command: "uv run python ../../manage.py test core"
# End:
