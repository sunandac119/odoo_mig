from odoo import models, fields

class SaleOrderLine(models.Model):
    _inherit = 'sale.order.line'

    pos_template_barcode = fields.Char(string='Template Barcode', compute='_compute_template_barcode', search='_search_template_barcode')

    def _compute_template_barcode(self):
        for rec in self:
            rec.pos_template_barcode = rec.product_id.product_tmpl_id.pos_lines.barcode

    def _search_template_barcode(self, operator, value):
        return [('product_id.product_tmpl_id.pos_lines.barcode', operator, value)]


class PurchaseOrderLine(models.Model):
    _inherit = 'purchase.order.line'

    pos_template_barcode = fields.Char(string='Template Barcode', compute='_compute_template_barcode', search='_search_template_barcode')

    def _compute_template_barcode(self):
        for rec in self:
            rec.pos_template_barcode = rec.product_id.product_tmpl_id.pos_lines.barcode

    def _search_template_barcode(self, operator, value):
        return [('product_id.product_tmpl_id.pos_lines.barcode', operator, value)]


class StockMoveLine(models.Model):
    _inherit = 'stock.move.line'

    pos_template_barcode = fields.Char(string='Template Barcode', compute='_compute_template_barcode', search='_search_template_barcode')

    def _compute_template_barcode(self):
        for rec in self:
            rec.pos_template_barcode = rec.product_id.product_tmpl_id.pos_lines.barcode

    def _search_template_barcode(self, operator, value):
        return [('product_id.product_tmpl_id.pos_lines.barcode', operator, value)]
