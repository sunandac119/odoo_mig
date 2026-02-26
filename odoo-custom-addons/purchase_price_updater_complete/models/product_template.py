from odoo import models, fields, api
from datetime import datetime, timedelta
import logging

_logger = logging.getLogger(__name__)

class ProductTemplate(models.Model):
    _inherit = 'product.template'

    @api.model
    def cron_update_standard_price(self):
        yesterday = (datetime.today() - timedelta(days=1)).strftime('%Y-%m-%d')

        # Fetch yesterday's purchase receipts (incoming stock moves)
        stock_moves = self.env['stock.move'].search([
            ('state', '=', 'done'),
            ('picking_type_id.code', '=', 'incoming'),  # Only incoming purchase receipts
            ('date', '>=', yesterday),
            ('date', '<', datetime.today().strftime('%Y-%m-%d'))
        ])

        if not stock_moves:
            _logger.info("No purchase receipts for yesterday.")
            return

        _logger.info(f"Found {len(stock_moves)} stock moves for yesterday.")

        # Process each stock move
        for move in stock_moves:
            try:
                product_variant = move.product_id
                product_template = product_variant.product_tmpl_id
                unit_qty = product_template.unit_qty or 1.0  # Avoid division by zero

                if product_template:
                    _logger.info(f"Processing product template ID: {product_template.id} with unit_qty: {unit_qty}")

                    # Step 1: Calculate the last purchase cost
                    last_purchase_cost = move.price_unit / unit_qty  # Divide price_unit by unit_qty to get last purchase cost per unit

                    # Step 2: Update the product.template standard_price for all products sharing the same parent_template_id
                    parent_template_id = product_template.parent_template_id

                    if parent_template_id:
                        _logger.info(f"Parent Template ID: {parent_template_id.id}")

                        # Get all products that share the same parent_template_id
                        same_parent_templates = self.search([('parent_template_id', '=', parent_template_id.id)])

                        # Update the standard_price for all products sharing the same parent_template_id
                        for template in same_parent_templates:
                            template_unit_qty = template.unit_qty or 1.0  # Ensure unit_qty is not zero

                            # Calculate new standard_price: last_purchase_cost * unit_qty
                            new_standard_price = last_purchase_cost * template_unit_qty

                            # Attempt to update the standard_price for the template
                            try:
                                template.sudo().write({
                                    'standard_price': new_standard_price
                                })
                                _logger.info(f"Updated product template ID {template.id} with new standard_price {new_standard_price}")
                            except Exception as write_error:
                                _logger.error(f"Failed to update standard_price for product template ID {template.id}: {str(write_error)}")

                        # Also update the parent template's standard_price with the last purchase cost
                        try:
                            parent_template_id.sudo().write({
                                'standard_price': last_purchase_cost
                            })
                            _logger.info(f"Updated parent template ID {parent_template_id.id} with standard_price {last_purchase_cost}")
                        except Exception as parent_write_error:
                            _logger.error(f"Failed to update standard_price for parent template ID {parent_template_id.id}: {str(parent_write_error)}")

                    else:
                        # If no parent template, update the product.template standard_price based on the last purchase cost
                        new_standard_price = last_purchase_cost * unit_qty
                        try:
                            product_template.sudo().write({
                                'standard_price': new_standard_price
                            })
                            _logger.info(f"Updated product template ID {product_template.id} with standard_price {new_standard_price}")
                        except Exception as template_write_error:
                            _logger.error(f"Failed to update standard_price for product template ID {product_template.id}: {str(template_write_error)}")

            except Exception as e:
                _logger.error(f"Error processing move ID {move.id}: {str(e)}")
