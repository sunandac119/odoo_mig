
from odoo import models, fields, api

class SaleOrderLine(models.Model):
    _inherit = 'sale.order.line'

    scanned_barcode = fields.Char(string="Scanned Barcode")

    @api.onchange('scanned_barcode')
    def _onchange_scanned_barcode(self):
        if self.scanned_barcode:
            barcode_line = self.env['product.barcode.uom'].search([
                ('barcode', '=', self.scanned_barcode)
            ], limit=1)
            if barcode_line:
                product_variant = self.env['product.product'].search([
                    ('product_tmpl_id', '=', barcode_line.product_id.id)
                ], limit=1)

                self.product_id = product_variant.id
                self.product_uom = barcode_line.uom_id.id
                self.price_unit = barcode_line.sale_price
            else:
                self.product_id = False
                self.product_uom = False
                self.price_unit = 0.0
