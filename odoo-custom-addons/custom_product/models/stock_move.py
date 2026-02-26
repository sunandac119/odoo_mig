from odoo import models, fields


class StockMove(models.Model):
    _inherit = 'stock.move'

    unit_qty = fields.Float(string='Unit Quantity', digits=(16, 2))

