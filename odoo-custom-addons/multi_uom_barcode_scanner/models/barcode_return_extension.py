
from odoo import models, fields, api
import logging

_logger = logging.getLogger(__name__)

class SaleReturnLine(models.Model):
    _inherit = 'sale.return.line'

    x_scanned_barcode = fields.Char(string="Scanned Barcode")

    @api.onchange('x_scanned_barcode')
    def _onchange_x_scanned_barcode(self):
        if not self.x_scanned_barcode:
            return
        barcode_line = self.env['f.pos.multi.uom.barcode.lines'].search([
            ('barcode', '=', self.x_scanned_barcode)
        ], limit=1)
        if barcode_line:
            product = self.env['product.product'].search([('product_tmpl_id', '=', barcode_line.uom_barcode.id)], limit=1)
            if product:
                self.product_id = product.id
                self.product_uom = barcode_line.uom.id
                self.price_unit = barcode_line.sale_price or product.lst_price

class PurchaseReturnLine(models.Model):
    _inherit = 'purchase.return.line'

    x_scanned_barcode = fields.Char(string="Scanned Barcode")

    @api.onchange('x_scanned_barcode')
    def _onchange_x_scanned_barcode(self):
        if not self.x_scanned_barcode:
            return
        barcode_line = self.env['f.pos.multi.uom.barcode.lines'].search([
            ('barcode', '=', self.x_scanned_barcode)
        ], limit=1)
        if barcode_line:
            product = self.env['product.product'].search([('product_tmpl_id', '=', barcode_line.uom_barcode.id)], limit=1)
            if product:
                self.product_id = product.id
                self.product_uom = barcode_line.uom.id
                self.price_unit = barcode_line.sale_price or product.lst_price
