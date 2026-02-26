from odoo import api, models

class BarcodeResolver(models.AbstractModel):
    _name = 'barcode.resolver.mixin'

    @api.model
    def resolve_pos_uom_barcode(self, barcode):
        barcode_rec = self.env['pos.uom.barcode'].search([('barcode', '=', barcode)], limit=1)
        if barcode_rec:
            return barcode_rec.product_id, barcode_rec.uom_id, barcode_rec.price
        return None, None, None
