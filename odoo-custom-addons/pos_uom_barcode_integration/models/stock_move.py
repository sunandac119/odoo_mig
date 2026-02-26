from odoo import models, api

class StockMove(models.Model):
    _inherit = 'stock.move'

    @api.onchange('product_id')
    def _onchange_product_id(self):
        if self.product_id and self.product_id.default_code:
            product, uom, price = self.env['barcode.resolver.mixin'].resolve_pos_uom_barcode(self.product_id.default_code)
            if product:
                self.product_id = product.id
                self.product_uom = uom.id
