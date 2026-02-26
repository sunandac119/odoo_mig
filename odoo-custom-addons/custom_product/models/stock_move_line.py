from odoo import models, fields


class StockMoveLine(models.Model):
    _inherit = 'stock.move.line'

    parent_product_template_id = fields.Many2one(
        'product.template',
        string='Parent Product Template',
        related='product_id.product_tmpl_id.parent_template_id',
        store=True,
        readonly=True,
    )
