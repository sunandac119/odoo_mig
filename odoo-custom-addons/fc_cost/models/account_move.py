from odoo import models, fields, api

class AccountMove(models.Model):
    _inherit = 'account.move'

    def button_post(self):
        # Call the original post method
        res = super(AccountMove, self).button_post()

        # Recalculate unit cost for vendor bills upon confirmation
        if self.move_type == 'in_invoice':  # Only for vendor bills
            for line in self.invoice_line_ids:
                product = line.product_id
                if not product:
                    continue

                product_variant_id = product.id  # Product variant ID

                # Trigger recalculation for this variant based on the linked stock moves
                self.env['product.product'].recalculate_variant_cost(product_variant_id)

        return res
