from odoo import models, fields, api
import logging

_logger = logging.getLogger(__name__)


class ProductPricelistItem(models.Model):
    _inherit = 'product.pricelist.item'

    x_scanned_barcode = fields.Char(string="Scanned Barcode")

    @api.onchange('x_scanned_barcode')
    def _onchange_x_scanned_barcode(self):
        if not self.x_scanned_barcode:
            return

        # Search directly in f.pos.multi.uom.barcode.lines
        barcode_line = self.env['f.pos.multi.uom.barcode.lines'].search([
            ('barcode', '=', self.x_scanned_barcode)
        ], limit=1)

        if barcode_line:
            # Set applied_on to product level first
            self.applied_on = '1_product'

            # Set the product template - uom_barcode is the product template
            self.product_tmpl_id = barcode_line.uom_barcode.id

            # Find the product variant
            product = self.env['product.product'].search([
                ('product_tmpl_id', '=', barcode_line.uom_barcode.id)
            ], limit=1)

            if product:
                self.product_id = product.id

            # Set the Pricelist UOM from barcode line - field name is uom_id as per your second image
            if barcode_line.uom:
                # Based on your second image, the field name is uom_id for Pricelist UOM
                if hasattr(self, 'uom_id'):
                    self.uom_id = barcode_line.uom.id
                else:
                    # Fallback for different field names
                    for field_name in ['pricelist_uom_id', 'product_uom', 'base_pricelist_uom']:
                        if hasattr(self, field_name):
                            setattr(self, field_name, barcode_line.uom.id)
                            break

            # Set price from barcode line
            if barcode_line.sale_price:
                self.fixed_price = barcode_line.sale_price

        else:
            # If no barcode line found, try standard product barcode
            products = self.env['product.product'].search([('barcode', '=', self.x_scanned_barcode)])
            if products:
                product = products[0]
                self.applied_on = '1_product'
                self.product_tmpl_id = product.product_tmpl_id.id
                self.product_id = product.id
                # Set default UOM
                if hasattr(self, 'uom_id'):
                    self.uom_id = product.uom_id.id

    @api.onchange('product_tmpl_id', 'product_id')
    def _onchange_product_id(self):
        # Call parent method first
        result = super()._onchange_product_id()
        return result


class ProductPricelist(models.Model):
    _inherit = 'product.pricelist'

    def _compute_price_rule(self, products_qty_partner, date=False, uom_id=False):
        """Override to handle multi-UOM barcode pricing"""
        result = super()._compute_price_rule(products_qty_partner, date, uom_id)

        # Check if context has UOM from barcode scan
        if self._context.get('uom'):
            scanned_uom_id = self._context.get('uom')
            for product, qty, partner in products_qty_partner:
                if product.id in result:
                    price, rule_id = result[product.id]

                    # Look for barcode line with this UOM
                    barcode_line = self.env['f.pos.multi.uom.barcode.lines'].search([
                        ('uom_barcode', '=', product.product_tmpl_id.id),
                        ('uom', '=', scanned_uom_id)
                    ], limit=1)

                    if barcode_line and barcode_line.sale_price:
                        # Use the price from barcode line if available
                        result[product.id] = (barcode_line.sale_price, rule_id)

        return result


class ProductTemplate(models.Model):
    _inherit = 'product.template'

    @api.model
    def name_search(self, name='', args=None, operator='ilike', limit=100):
        args = args or []
        if name:
            # First check if it's a barcode from f.pos.multi.uom.barcode.lines
            barcode_line = self.env['f.pos.multi.uom.barcode.lines'].search([
                ('barcode', '=', name)
            ], limit=1)

            if barcode_line:
                # Return the product template
                product_template = barcode_line.uom_barcode
                return product_template.name_get()

        return super().name_search(name=name, args=args, operator=operator, limit=limit)