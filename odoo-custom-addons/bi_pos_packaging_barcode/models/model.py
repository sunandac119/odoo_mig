from odoo import fields, models, api
from odoo.exceptions import AccessError


class ProductPackaging(models.Model):
    _inherit = 'product.packaging'

    _sql_constraints = [
        ('positive_qty', 'CHECK(qty > 0)', 'Contained Quantity should be positive.'),
        ('unique_barcode', 'UNIQUE(barcode)', 'Barcode must be unique.'),
    ]
	
    list_price = fields.Float(string='List Price')

    def _check_qty(self, product_qty, uom_id, rounding_method="HALF-UP"):
        """Check if product_qty in given uom is a multiple of the packaging qty.
        If not, rounding the product_qty to closest multiple of the packaging qty
        according to the rounding_method "UP", "HALF-UP or "DOWN".
        """
        self.ensure_one()
        default_uom = self.product_id.uom_id
        packaging_qty = default_uom._compute_quantity(self.qty, uom_id)
        # We do not use the modulo operator to check if qty is a mltiple of q. Indeed the quantity
        # per package might be a float, leading to incorrect results. For example:
        # 8 % 1.6 = 1.5999999999999996
        # 5.4 % 1.8 = 2.220446049250313e-16
        if product_qty and packaging_qty:
            rounded_qty = float_round(product_qty / packaging_qty, precision_rounding=1.0,
                                  rounding_method=rounding_method) * packaging_qty
            return rounded_qty if float_compare(rounded_qty, product_qty, precision_rounding=default_uom.rounding) else product_qty
        return product_qty

    def _find_suitable_product_packaging(self, product_qty, uom_id):
        """ try find in `self` if a packaging's qty in given uom is a divisor of
        the given product_qty. If so, return the one with greatest divisor.
        """
        packagings = self.sorted(lambda p: p.qty, reverse=True)
        for packaging in packagings:
            new_qty = packaging._check_qty(product_qty, uom_id)
            if new_qty == product_qty:
                return packaging
        return self.env['product.packaging']

    




