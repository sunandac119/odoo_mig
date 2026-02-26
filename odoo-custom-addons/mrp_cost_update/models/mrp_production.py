from odoo import models, api

class MrpProduction(models.Model):
    _inherit = 'mrp.production'

    def button_mark_done(self):
        res = super(MrpProduction, self).button_mark_done()
        self.update_product_standard_price()
        return res

    def update_product_standard_price(self):
        for production in self:
            total_cost = 0.0
            for move in production.move_raw_ids:
                total_cost += move.product_id.standard_price * move.product_uom_qty

            unit_cost = total_cost / production.product_qty if production.product_qty else 0

            # Update the standard_price for product.product
            production.product_id.standard_price = unit_cost
