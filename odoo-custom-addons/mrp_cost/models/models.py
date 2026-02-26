from odoo import models, fields, api

class MrpProduction(models.Model):
    _inherit = 'mrp.production'

    def update_standard_price(self):
        for order in self:
            total_cost = sum(move.product_id.standard_price * move.product_qty for move in order.move_raw_ids)
            if order.product_id:
                order.product_id.product_tmpl_id.write({'standard_price': total_cost / order.product_qty})
