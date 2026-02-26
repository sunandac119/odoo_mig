from odoo import models, fields, api
from datetime import datetime, timedelta

class ProductTemplate(models.Model):
    _inherit = 'product.template'

    @api.depends('product_variant_ids.qty_available', 'unit_qty')
    def _compute_parent_qty_available(self):
        for template in self:
            if template.unit_qty != 0:
                if template.parent_template_id:
                    same_parent_templates = self.search([('parent_template_id', '=', template.parent_template_id.id)])
                    total_qty_available = sum(
                        variant.qty_available * product_template.unit_qty * product_template.ctn_qty
                        for product_template in same_parent_templates
                        for variant in product_template.product_variant_ids
                    )
                    template.parent_qty_available = total_qty_available
                else:
                    template.parent_qty_available = sum(
                        variant.qty_available * template.unit_qty * template.ctn_qty
                        for variant in template.product_variant_ids
                    )
            else:
                template.parent_qty_available = 0.0

    @api.depends('product_variant_ids.qty_available', 'unit_qty')
    def _compute_costs(self):
        for template in self:
            if template.unit_qty != 0:
                if template.parent_template_id:
                    same_parent_templates = self.search([('parent_template_id', '=', template.parent_template_id.id)])
                    total_purchase_cost = 0.0
                    total_sale_cost = 0.0
                    total_sale_return_cost = 0.0
                    total_purchase_return_cost = 0.0

                    for product_template in same_parent_templates:
                        moves = self.env['stock.move'].search([
                            ('product_id', 'in', product_template.product_variant_ids.ids),
                            ('state', '=', 'done'),
                        ])

                        for move in moves:
                            qty_factor = product_template.unit_qty * product_template.ctn_qty
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
                    template.purchase_cost = sum(
                        variant.purchase_cost * template.unit_qty * template.ctn_qty
                        for variant in template.product_variant_ids.filtered(
                            lambda variant: variant.purchase_line_id and not variant.origin_returned_move_id
                        )
                    )
                    template.sale_cost = sum(
                        variant.sale_cost * template.unit_qty * template.ctn_qty
                        for variant in template.product_variant_ids.filtered(
                            lambda variant: variant.sale_line_id and not variant.origin_returned_move_id
                        )
                    )
                    template.purchase_return_cost = sum(
                        variant.purchase_return_cost * template.unit_qty * template.ctn_qty
                        for variant in template.product_variant_ids.filtered(
                            lambda variant: variant.purchase_line_id and variant.origin_returned_move_id
                        )
                    )
                    template.sale_return_cost = sum(
                        variant.sale_return_cost * template.unit_qty * template.ctn_qty
                        for variant in template.product_variant_ids.filtered(
                            lambda variant: variant.sale_line_id and variant.origin_returned_move_id
                        )
                    )
            else:
                template.purchase_cost = 0.0
                template.sale_cost = 0.0
                template.purchase_return_cost = 0.0
                template.sale_return_cost = 0.0

    @api.model
    def cron_update_lastcost(self):
        yesterday = (datetime.today() - timedelta(days=1)).strftime('%Y-%m-%d')

        # Fetch yesterday's purchase receipts (incoming stock moves)
        stock_moves = self.env['stock.move'].search([
            ('state', '=', 'done'),
            ('picking_type_id.code', '=', 'incoming'),  # Only incoming purchase receipts
            ('date', '>=', yesterday),
            ('date', '<', datetime.today().strftime('%Y-%m-%d'))
        ])

        if not stock_moves:
            print("No purchase receipts for yesterday.")
            return

        print(f"Found {len(stock_moves)} stock moves for yesterday.")

        # Dictionary to group moves by product_template
        grouped_moves = {}

        # Group stock moves by product_template_id
        for move in stock_moves:
            product_template = move.product_id.product_tmpl_id

            if product_template:
                if product_template.id not in grouped_moves:
                    grouped_moves[product_template.id] = {'total_cost': 0.0, 'total_qty': 0.0, 'product_template': product_template}

                # Sum up total cost and quantity for the same product template
                grouped_moves[product_template.id]['total_cost'] += move.price_unit * move.product_qty
                grouped_moves[product_template.id]['total_qty'] += move.product_qty

        # Process each product template
        for product_template_id, data in grouped_moves.items():
            product_template = data['product_template']
            total_cost = data['total_cost']
            total_qty = data['total_qty'] or 1.0  # Avoid division by zero

            # Calculate last purchase cost
            last_purchase_cost = total_cost / total_qty

            # Get parent template ID (if it exists)
            parent_template_id = product_template.parent_template_id

            if parent_template_id:
                print(f"Parent Template ID: {parent_template_id.id}")

                # Get all products that share the same parent_template_id
                same_parent_templates = self.search([('parent_template_id', '=', parent_template_id.id)])

                # Update the standard_price for all products sharing the same parent_template_id
                for template in same_parent_templates:
                    new_standard_price = last_purchase_cost * (template.unit_qty or 1.0)

                    # Update the standard_price for the template
                    template.sudo().write({
                        'standard_price': new_standard_price
                    })
                    print(f"Updated standard_price for product template ID: {template.id} to {new_standard_price}")

                # Also update the parent template's standard_price
                parent_template_id.sudo().write({
                    'standard_price': last_purchase_cost
                })
                print(f"Updated parent template standard_price to {last_purchase_cost}")

            else:
                # If no parent template, update the standard_price for the individual product template
                new_standard_price = last_purchase_cost * (product_template.unit_qty or 1.0)

                product_template.sudo().write({
                    'standard_price': new_standard_price
                })
                print(f"Updated standard_price for product template ID: {product_template.id} to {new_standard_price}")
