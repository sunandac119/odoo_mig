from odoo import models, api

class SaleOrderLine(models.Model):
    _inherit = 'sale.order.line'

    @api.onchange('product_id')
    def _onchange_product_id(self):
        if self.product_id and self.product_id.default_code:
            product, uom, price = self.env['barcode.resolver.mixin'].resolve_pos_uom_barcode(self.product_id.default_code)
            if product:
                self.product_id = product.id
                self.product_uom = uom.id
                self.price_unit = price
