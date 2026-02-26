from odoo import api, fields, models, _

class SaleOrderLine(models.Model):
    _inherit = 'sale.order.line'

    standard_price = fields.Float("Standard Price", related="product_id.standard_price", store=True)