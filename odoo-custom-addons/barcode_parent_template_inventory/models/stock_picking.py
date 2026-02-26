from odoo import models, api

class StockPicking(models.Model):
    _inherit = 'stock.picking'

    @api.model
    def _get_product_from_barcode(self, barcode):
        """Custom barcode resolver with parent_template_id logic."""
        Product = self.env['product.product']
        product = Product.search([('barcode', '=', barcode)], limit=1)

        if not product:
            # Try finding via product.template and parent_template_id
            ProductTemplate = self.env['product.template']
            template = ProductTemplate.search([
                ('barcode', '=', barcode)
            ], limit=1)

            if template and template.parent_template_id:
                product = Product.search([
                    ('product_tmpl_id', '=', template.parent_template_id.id)
                ], limit=1)

        return product