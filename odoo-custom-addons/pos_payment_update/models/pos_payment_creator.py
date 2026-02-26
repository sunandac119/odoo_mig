from odoo import models, fields, api

class PosPaymentCreator(models.TransientModel):
    _name = 'pos.payment.creator'

    def create_missing_payments(self):
        paid_orders = self.env['pos.order'].search([('state', '=', 'paid')])
        for order in paid_orders:
            if not order.payment_ids:
                self.env['pos.payment'].create({
                    'pos_order_id': order.id,
                    'amount': order.amount_paid,
                    # Add other fields if needed
                })
        return True
