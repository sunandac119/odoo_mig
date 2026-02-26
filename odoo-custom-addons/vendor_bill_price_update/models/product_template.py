from odoo import models, fields, api
from datetime import timedelta
import logging

_logger = logging.getLogger(__name__)

class ProductTemplate(models.Model):
    _inherit = 'product.template'

    @api.model
    def cron_reupdate_standard_price_vendor_bill(self):
        """
        Cron job: Recalculate and update standard_price based on vendor bills posted yesterday.
        """
        # Calculate yesterday's date range
        yesterday = fields.Datetime.now() - timedelta(days=1)
        yesterday_start = yesterday.date()
        yesterday_end = yesterday.date()

        _logger.info("Fetching vendor bills posted yesterday...")

        # Fetch posted vendor bills from yesterday
        vendor_bills = self.env['account.move'].search([
            ('state', '=', 'posted'),
            ('move_type', '=', 'in_invoice'),
            ('invoice_date', '>=', yesterday_start),
            ('invoice_date', '<=', yesterday_end)
        ])

        if not vendor_bills:
            _logger.info("No vendor bills posted yesterday. Nothing to update.")
            return

        _logger.info(f"Found {len(vendor_bills)} vendor bills. Processing lines to update standard_price...")

        # Dictionary to aggregate costs and quantities for parent templates
        parent_template_data = {}

        for bill in vendor_bills:
            for line in bill.invoice_line_ids:
                product = line.product_id
                if not product or not product.product_tmpl_id:
                    continue

                product_template = product.product_tmpl_id
                parent_template = product_template.parent_template_id

                if not parent_template:
                    continue

                qty = line.quantity
                total_cost = line.price_subtotal

                if parent_template.id not in parent_template_data:
                    parent_template_data[parent_template.id] = {'total_qty': 0, 'total_cost': 0}

                parent_template_data[parent_template.id]['total_qty'] += qty
                parent_template_data[parent_template.id]['total_cost'] += total_cost

        # Update parent and child templates
        for parent_template_id, data in parent_template_data.items():
            total_qty = data['total_qty']
            total_cost = data['total_cost']

            if total_qty > 0:
                # Calculate new average price
                new_standard_price = total_cost / total_qty
                parent_template = self.env['product.template'].browse(parent_template_id)

                # Update parent template standard_price
                parent_template.write({'standard_price': new_standard_price})

                # Update child templates based on unit_qty
                child_templates = self.env['product.template'].search([
                    ('parent_template_id', '=', parent_template_id)
                ])
                for template in child_templates:
                    child_standard_price = new_standard_price * (template.unit_qty or 1)
                    for variant in template.product_variant_ids:
                        variant.sudo().write({'standard_price': child_standard_price})

                    _logger.info(f"Updated product '{template.name}' (ID: {template.id}) "
                                 f"with new standard price {child_standard_price:.2f}")

        _logger.info("Standard price update based on vendor bills completed successfully.")

    @api.model
    def create_vendor_bill_cron_job(self):
        """Create a cron job to reupdate standard price based on vendor bills."""
        cron_name = 'Reupdate Standard Price from Vendor Bills'
        cron = self.env['ir.cron'].search([('name', '=', cron_name)], limit=1)

        if not cron:
            self.env['ir.cron'].create({
                'name': cron_name,
                'model_id': self.env['ir.model']._get('product.template').id,
                'state': 'code',
                'code': "model.cron_reupdate_standard_price_vendor_bill()",
                'interval_type': 'days',
                'interval_number': 1,
                'numbercall': -1,
                'nextcall': fields.Datetime.now() + timedelta(minutes=10),  # Starts in 10 minutes
            })
