import csv
from odoo import models, fields, api

class AccountMove(models.Model):
    _inherit = 'account.move'

    def button_post(self):
        # Call the original button_post to confirm the vendor bill
        res = super(AccountMove, self).button_post()

        # Perform standard_price update on vendor bill confirmation
        if self.move_type == 'in_invoice':  # Only apply to vendor bills
            self.update_standard_price_on_confirmation()

        return res

    def update_standard_price_on_confirmation(self):
        results = []

        for line in self.invoice_line_ids:
            move = line.move_id.stock_move_id  # Get the stock move linked to this invoice line
            if not move:
                continue

            product_template = line.product_id.product_tmpl_id
            if not product_template or not product_template.parent_template_id:
                continue

            parent_template = product_template.parent_template_id
            last_purchase_price = line.price_unit

            if last_purchase_price > 0 and product_template.ctn_qty:
                new_parent_standard_price = last_purchase_price / product_template.ctn_qty

                # Update parent template's standard price
                parent_template.sudo().write({'standard_price': new_parent_standard_price})

                # Update all child templates with the same parent template
                child_templates = self.env['product.template'].search([
                    ('parent_template_id', '=', parent_template.id)
                ])

                for child_template in child_templates:
                    old_standard_price = child_template.standard_price
                    new_standard_price = new_parent_standard_price * (child_template.unit_qty or 1)

                    # Update child template's standard price
                    child_template.sudo().write({'standard_price': new_standard_price})

                    # Log results for debugging or reporting
                    results.append({
                        'product_id': child_template.id,
                        'product_name': child_template.name,
                        'parent_template_id': parent_template.id,
                        'parent_template_name': parent_template.name,
                        'unit_qty': child_template.unit_qty or 1,
                        'barcode': child_template.barcode,
                        'ctn_qty': child_template.ctn_qty or 1,
                        'vendor_price': last_purchase_price,
                        'old_standard_price': old_standard_price,
                        'new_standard_price': new_standard_price
                    })

        # Save results to a CSV file for audit purposes
        csv_file = '/tmp/updated_standard_prices.csv'
        with open(csv_file, mode='w', newline='') as file:
            writer = csv.DictWriter(file, fieldnames=['product_id', 'product_name', 'parent_template_id', 'parent_template_name', 'unit_qty', 'barcode', 'ctn_qty', 'vendor_price', 'old_standard_price', 'new_standard_price'])
            writer.writeheader()
            for row in results:
                writer.writerow(row)

        print(f"Standard prices updated and saved to {csv_file}")
