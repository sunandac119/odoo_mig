
from odoo import models, fields, api

class PurchaseOrderLine(models.Model):
    _inherit = 'purchase.order.line'

    product_barcode = fields.Char(string="Scanned Barcode")

    @api.onchange('product_barcode')
    def _onchange_product_barcode(self):
        if self.product_barcode:
            mapping = self.env['product.uom.mapping'].search([('barcode', '=', self.product_barcode)], limit=1)
            if mapping:
                product = self.env['product.product'].search([('product_tmpl_id', '=', mapping.product_tmpl_id.id)], limit=1)
                self.product_id = product
                self.product_uom = mapping.uom_id
                self.product_qty = mapping.factor
                self.price_unit = mapping.price
