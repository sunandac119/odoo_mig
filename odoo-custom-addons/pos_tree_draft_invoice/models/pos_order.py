from odoo import models, fields, api, _
from odoo.exceptions import UserError

class PosOrder(models.Model):
    _inherit = 'pos.order'

    invoice_id = fields.Many2one('account.move', string="Invoice", readonly=True)

    def action_create_invoice(self):
        """
        Combine all POS orders for the same customer into a single invoice, 
        grouping by product and summing quantity and sales amount.
        """
        if not self:
            raise UserError(_("No POS orders selected."))

        invoices = self.env['account.move']
        grouped_orders = {}

        # Group orders by customer
        for order in self:
            if not order.partner_id:
                raise UserError(_("Please set a customer for the POS order to generate an invoice."))
            if order.invoice_id:
                continue
            grouped_orders.setdefault(order.partner_id, []).append(order)

        # Create invoices for each customer
        for partner, orders in grouped_orders.items():
            journal = self.env['account.journal'].search(
                [('type', '=', 'sale'), ('company_id', '=', orders[0].company_id.id)], limit=1
            )
            if not journal:
                raise UserError(_("No sales journal found for company %s.") % orders[0].company_id.name)

            invoice_vals = {
                'move_type': 'out_invoice',
                'partner_id': partner.id,
                'journal_id': journal.id,
                'invoice_origin': ', '.join(order.name for order in orders),
                'currency_id': orders[0].currency_id.id,
                'invoice_line_ids': [],
            }

            # Group by product and sum sales amount & quantity
            product_totals = {}
            for order in orders:
                for line in order.lines:
                    product = line.product_id
                    if product not in product_totals:
                        product_totals[product] = {
                            'quantity': 0,
                            'price_subtotal': 0,
                            'tax_ids': set(line.tax_ids_after_fiscal_position.ids),
                            'account_id': product.categ_id.property_account_income_categ_id.id or journal.default_account_id.id,
                        }
                    product_totals[product]['quantity'] += line.qty
                    product_totals[product]['price_subtotal'] += line.qty * line.price_unit

            # Create invoice lines from grouped product data
            for product, values in product_totals.items():
                invoice_line_vals = {
                    'name': product.display_name,
                    'product_id': product.id,
                    'quantity': values['quantity'],
                    'price_unit': values['price_subtotal'] / values['quantity'] if values['quantity'] else 0,
                    'tax_ids': [(6, 0, list(values['tax_ids']))],
                    'account_id': values['account_id'],
                }
                invoice_vals['invoice_line_ids'].append((0, 0, invoice_line_vals))

            # Create and post the invoice
            invoice = invoices.create(invoice_vals)
            invoice.action_post()

            # Link the orders to the invoice
            for order in orders:
                order.invoice_id = invoice.id

        return True
