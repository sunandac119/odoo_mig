from odoo import models, fields, api

class ProductTemplate(models.Model):
    _inherit = 'product.template'

    def update_barcode_with_check_digit(self):
        for record in self:
            if record.name and len(record.name) == 12:
                check_digit = self._calculate_ean_check_digit(record.name)
                record.barcode = record.name + str(check_digit)

    @staticmethod
    def _calculate_ean_check_digit(barcode_digits):
        total = sum(int(digit) * (3 if index % 2 == 0 else 1) for index, digit in enumerate(reversed(barcode_digits)))
        return (10 - (total % 10)) % 10
