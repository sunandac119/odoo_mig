from odoo import models, fields, api

class MrpBom(models.Model):
    _inherit = 'mrp.bom'

    x_actual_component_qty = fields.Float("Actual Component Qty (BAG)", help="User input of component quantity")
    x_estimated_final_qty = fields.Float("Estimated Can Produce Qty", compute="_compute_estimated_final_qty")

    @api.depends('x_actual_component_qty', 'bom_line_ids')
    def _compute_estimated_final_qty(self):
        for bom in self:
            bom_output_qty = bom.product_qty
            if bom_output_qty == 0 or not bom.bom_line_ids:
                bom.x_estimated_final_qty = 0
                continue

            bom_line = bom.bom_line_ids[0]
            component_qty_in_bom = bom_line.product_qty

            if component_qty_in_bom == 0:
                bom.x_estimated_final_qty = 0
                continue

            ratio = bom_output_qty / component_qty_in_bom
            bom.x_estimated_final_qty = ratio * bom.x_actual_component_qty

    def action_recalculate_product_qty(self):
        for bom in self:
            if not bom.bom_line_ids:
                continue
            bom_line = bom.bom_line_ids[0]
            if bom_line.product_qty == 0:
                continue
            # Inverse logic: set product_qty = ratio * actual component qty
            ratio = bom.product_qty / bom_line.product_qty
            bom.product_qty = ratio * bom.x_actual_component_qty
