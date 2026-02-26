from odoo import models, api

class StockInventory(models.Model):
    _inherit = 'stock.inventory'

    @api.model
    def _get_product_from_barcode(self, barcode):
        Product = self.env['product.product']
        product = Product.search([('barcode', '=', barcode)], limit=1)

        if not product:
            # Check product.template directly
            template = self.env['product.template'].search([('barcode', '=', barcode)], limit=1)
            if template:
                # First: try to find variant of this template
                product = Product.search([('product_tmpl_id', '=', template.id)], limit=1)

                # Then: if parent_template_id is defined, fallback to its variants
                if not product and template.parent_template_id:
                    product = Product.search([
                        ('product_tmpl_id', '=', template.parent_template_id.id)
                    ], limit=1)

        return product