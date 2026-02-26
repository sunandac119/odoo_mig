from odoo import models

class ProductProduct(models.Model):
    _inherit = 'product.product'

    def name_search(self, name='', args=None, operator='ilike', limit=100):
        results = super().name_search(name, args=args, operator=operator, limit=limit)
        if results:
            return results

        # Fallback to searching by UoM barcode
        uom_lines = self.env['f.pos.multi.uom.barcode.lines'].search([('uom_barcode', '=', name)], limit=limit)
        products = uom_lines.mapped('product_id')
        return products.name_get()