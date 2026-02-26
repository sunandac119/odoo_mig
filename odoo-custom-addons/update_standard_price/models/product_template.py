from odoo import models, api
import logging

_logger = logging.getLogger(__name__)

class ProductTemplate(models.Model):
    _inherit = 'product.template'

    @api.model
    def cron_update_standard_price(self):
        """Update parent & child standard_price based on weighted average from yesterday's purchase moves."""
        # Calculate yesterday's date range
        yesterday_start = (fields.Datetime.now() - timedelta(days=1)).replace(hour=0, minute=0, second=0)
        yesterday_end = yesterday_start.replace(hour=23, minute=59, second=59)

        # Fetch stock moves from yesterday
        move_ids = self.env['stock.move'].search([
            ('state', '=', 'done'),
            ('date', '>=', yesterday_start),
            ('date', '<=', yesterday_end),
            ('purchase_line_id', '!=', False)
        ], order='date desc')

        if not move_ids:
            _logger.info("No purchase receipts for the specified date range.")
            return

        parent_price_updates = {}

        for move in move_ids:
            product_template = move.product_id.product_tmpl_id
            if not product_template or not product_template.parent_template_id:
                continue

            parent_template = product_template.parent_template_id
            unit_qty = product_template.unit_qty or 1.0

            # Fetch purchase order line subtotal
            purchase_line = move.purchase_line_id
            total_purchase_value = purchase_line.price_subtotal
            quantity_done = move.quantity_done

            if parent_template.id not in parent_price_updates:
                parent_price_updates[parent_template.id] = {'total_price': 0, 'total_weighted_qty': 0}

            parent_price_updates[parent_template.id]['total_price'] += total_purchase_value
            parent_price_updates[parent_template.id]['total_weighted_qty'] += (quantity_done * unit_qty)

        updates_count = 0

        # Update parent and child templates
        for parent_template_id, data in parent_price_updates.items():
            total_price = data['total_price']
            total_weighted_qty = data['total_weighted_qty']

            if total_weighted_qty > 0:
                new_standard_price = round(total_price / total_weighted_qty, 3)

                parent_template = self.env['product.template'].browse(parent_template_id)
                old_parent_price = parent_template.standard_price
                parent_template.write({'standard_price': new_standard_price})
                _logger.info(f"Updated parent template {parent_template.name} ({parent_template.id}) "
                             f"from {old_parent_price} to {new_standard_price}")
                updates_count += 1

                # Update child templates
                same_parent_templates = self.env['product.template'].search([
                    ('parent_template_id', '=', parent_template.id)
                ])
                for template in same_parent_templates:
                    old_price = template.standard_price
                    new_price = round(new_standard_price * (template.unit_qty or 1.0), 2)
                    template.write({'standard_price': new_price})
                    _logger.info(f"  Updated child template {template.name} ({template.id}) "
                                 f"from {old_price} to {new_price}")
                    updates_count += 1

        _logger.info(f"cron_update_standard_price: Completed. Total products updated: {updates_count}")
