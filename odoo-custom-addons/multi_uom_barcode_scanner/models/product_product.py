from odoo import models, api

class ProductProduct(models.Model):
    _inherit = 'product.product'

    @api.model
    def name_search(self, name='', args=None, operator='ilike', limit=100):
        args = args or []
        if name:
            products = self.search([('barcode', '=', name)] + args, limit=limit)
            if not products:
                barcode_line = self.env['f.pos.multi.uom.barcode.lines'].search([('barcode', '=', name)], limit=1)
                if barcode_line:
                    product = barcode_line.uom_barcode.product_variant_id
                    return product.name_get()
        return super().name_search(name=name, args=args, operator=operator, limit=limit)
