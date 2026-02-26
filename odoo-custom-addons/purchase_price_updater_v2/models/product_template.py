from odoo import models, fields, api
from datetime import datetime, timedelta
import logging

_logger = logging.getLogger(__name__)

class ProductTemplate(models.Model):
    _inherit = 'product.template'

    @api.model
    def cron_update_standard_price(self):
        yesterday = (datetime.today() - timedelta(days=5)).strftime('%Y-%m-%d')
        today = datetime.today().strftime('%Y-%m-%d')

        # Fetch vendor bills with state = 'posted' and modified (write_date) yesterday
        vendor_bills = self.env['account.move'].search([
            ('state', '=', 'posted'),
            ('move_type', '=', 'in_invoice'),
            ('write_date', '>=', yesterday),
            ('write_date', '<', today)
        ])

        if not vendor_bills:
            _logger.info("No vendor bills with state 'posted' modified yesterday.")
            return

        _logger.info(f"Found {len(vendor_bills)} vendor bills modified yesterday.")

        # Process each vendor bill
        for bill in vendor_bills:
            try:
                # Loop through the lines in the vendor bill
                for line in bill.invoice_line_ids:
                    product_variant = line.product_id
                    product_template = product_variant.product_tmpl_id
                    unit_qty = product_template.unit_qty or 1.0  # Avoid division by zero

                    if product_template:
                        _logger.info(f"Processing product template ID: {product_template.id} with unit_qty: {unit_qty}")

                        # Step 1: Calculate the last purchase cost
                        last_purchase_cost = line.price_unit / unit_qty  # Divide price_unit by unit_qty to get last purchase cost per unit

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
                _logger.error(f"Error processing bill ID {bill.id}: {str(e)}")
