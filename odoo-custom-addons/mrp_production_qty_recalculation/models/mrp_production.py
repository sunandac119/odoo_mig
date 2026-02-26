from odoo import models, fields

class MrpProduction(models.Model):
    _inherit = 'mrp.production'

    x_actual_component_qty = fields.Float("Actual Component Qty (BAG)", help="User input for component qty to use")
    x_recalculated_product_qty = fields.Float("Recalculated Product Qty", readonly=True)

    def action_recalculate_qty_from_component(self):
        for production in self:
            if not production.bom_id or not production.bom_id.bom_line_ids:
                production.x_recalculated_product_qty = 0
                continue

            bom_line = production.bom_id.bom_line_ids[0]
            if bom_line.product_qty == 0:
                production.x_recalculated_product_qty = 0
                continue

            bom_ratio = production.bom_id.product_qty / bom_line.product_qty
            new_qty = bom_ratio * production.x_actual_component_qty
            production.x_recalculated_product_qty = new_qty
            production.product_qty = new_qty
