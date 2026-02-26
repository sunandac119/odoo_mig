from odoo import models, fields, api
from datetime import datetime, timedelta

class ProductTemplate(models.Model):
    _inherit = 'product.template'

    parent_template_id = fields.Many2one('product.template', string='Parent Template')
    parent_qty_available = fields.Float('Parent Qty Available', compute='_compute_parent_qty_available')
    ctn_qty = fields.Float(string='CTN Qty', digits=(16, 2))
    unit_qty = fields.Float(string='Unit Qty', digits=(16, 2))
    unit_uom = fields.Float(string='Unit UOM', digits=(16, 2))
    total_cost = fields.Float(string='Total Cost', digits=(16, 2))
    total_done_qty = fields.Float(string='Total Done Qty', digits=(16, 2))
    purchase_cost = fields.Float(string='Purchase Cost', digits=(16, 2), compute='_compute_costs')
    sale_cost = fields.Float(string='Sale Cost', digits=(16, 2), compute='_compute_costs')
    sale_return_cost = fields.Float(string='Sale Return Cost', digits=(16, 2), compute='_compute_costs')
    purchase_return_cost = fields.Float(string='Purchase Return Cost', digits=(16, 2), compute='_compute_costs')

    @api.depends('product_variant_ids.qty_available', 'unit_qty', 'ctn_qty')
    def _compute_parent_qty_available(self):
        for template in self:
            if template.unit_qty:
                same_parent_templates = self.search([('parent_template_id', '=', template.parent_template_id.id)]) if template.parent_template_id else [template]
                total_qty_available = sum(
                    variant.qty_available * product_template.unit_qty
                    for product_template in same_parent_templates
                    for variant in product_template.product_variant_ids
                )
                template.parent_qty_available = total_qty_available
            else:
                template.parent_qty_available = 0.0

    @api.depends('product_variant_ids.qty_available', 'unit_qty', 'ctn_qty')
    def _compute_costs(self):
        for template in self:
            if template.unit_qty:
                same_parent_templates = self.search([('parent_template_id', '=', template.parent_template_id.id)]) if template.parent_template_id else [template]
                total_purchase_cost = total_sale_cost = total_purchase_return_cost = total_sale_return_cost = 0.0

                for product_template in same_parent_templates:
                    stock_moves = self.env['stock.move'].search([
                        ('product_id', 'in', product_template.product_variant_ids.ids),
                        ('state', '=', 'done')
                    ])

                    for move in stock_moves:
                        qty_factor = product_template.unit_qty * product_template.ctn_qty or 1.0
                        if move.purchase_line_id and not move.origin_returned_move_id:
                            total_purchase_cost += move.price_unit * move.quantity_done * qty_factor
                        elif move.sale_line_id and not move.origin_returned_move_id:
                            total_sale_cost += move.sale_line_id.cost * move.quantity_done * qty_factor
                        elif move.sale_line_id and move.origin_returned_move_id:
                            total_sale_return_cost += move.price_unit * move.quantity_done * qty_factor
                        elif move.purchase_line_id and move.origin_returned_move_id:
                            total_purchase_return_cost += move.origin_returned_move_id.price_unit * move.quantity_done * qty_factor

                template.purchase_cost = total_purchase_cost
                template.sale_cost = total_sale_cost
                template.purchase_return_cost = total_purchase_return_cost
                template.sale_return_cost = total_sale_return_cost
            else:
                template.purchase_cost = template.sale_cost = template.purchase_return_cost = template.sale_return_cost = 0.0

    @api.model
    def cron_update_lastcost(self):
        # Set date range for yesterday's stock moves
        yesterday = (datetime.today() - timedelta(days=1)).replace(hour=0, minute=0, second=0)
        today = datetime.today().replace(hour=0, minute=0, second=0)

        # Fetch incoming stock moves for yesterday
        stock_moves = self.env['stock.move'].search([
            ('state', '=', 'done'),
            ('picking_type_id.code', '=', 'incoming'),
            ('date', '>=', yesterday),
            ('date', '<', today)
        ])

        if not stock_moves:
            return

        # Dictionary to group moves by parent_template_id
        grouped_moves = {}

        for move in stock_moves:
            product_template = move.product_id.product_tmpl_id
            parent_template_id = product_template.parent_template_id

            if parent_template_id:
                if parent_template_id.id not in grouped_moves:
                    grouped_moves[parent_template_id.id] = {'total_cost': 0.0, 'total_qty': 0.0, 'unit_qty': parent_template_id.unit_qty or 1.0}

                # Only consider moves with non-zero price_unit
                if move.price_unit > 0:
                    total_cost = move.price_unit * move.product_qty
                    total_qty_adjusted = move.product_qty * product_template.unit_qty

                    grouped_moves[parent_template_id.id]['total_cost'] += total_cost
                    grouped_moves[parent_template_id.id]['total_qty'] += total_qty_adjusted

        # Process each parent_template_id group
        for parent_template_id, data in grouped_moves.items():
            total_cost = data['total_cost']
            total_qty = data['total_qty'] or 1.0  # Avoid division by zero
            unit_qty = data['unit_qty'] or 1.0  # Avoid division by zero

            # Calculate last purchase cost using the XML-RPC formula
            last_purchase_cost = total_cost / (total_qty * unit_qty)

            # Update all templates with the same parent_template_id
            same_parent_templates = self.search([('parent_template_id', '=', parent_template_id)])
            for template in same_parent_templates:
                new_standard_price = last_purchase_cost * (template.unit_qty or 1.0)

                # Update the standard_price for each template
                template.sudo().write({'standard_price': new_standard_price})

            # Update the parent template's standard_price
            parent_template = self.browse(parent_template_id)
            parent_template.sudo().write({'standard_price': last_purchase_cost})

        return True
