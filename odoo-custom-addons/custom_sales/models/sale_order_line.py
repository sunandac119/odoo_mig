from odoo import models, fields

class SaleOrderLine(models.Model):
    _inherit = 'sale.order.line'

    cost = fields.Float('Cost', digits=(16, 2), compute='_compute_cost', store=True)

    def _compute_cost(self):
        for line in self:
            line.cost = line.product_id.standard_price
