from odoo import api, fields, models
from datetime import datetime


class PosOrder(models.Model):
    _inherit = 'pos.order'

    def create_from_ui(self, orders, draft=False):
        res = super(PosOrder, self).create_from_ui(orders=orders, draft=draft)
        todays_lhdn_retails_invoice = self.env['account.move'].search(
            [('move_type', '=', 'out_invoice'), ('invoice_date', '=', datetime.now().date()), ('state', '=', 'draft'),
             ('is_lhdn_pos_retail_combine_invoice', '=', True)], limit=1)
        if not todays_lhdn_retails_invoice:
            todays_lhdn_retails_invoice = self.env['account.move'].create({
                'move_type': 'out_invoice',
                'invoice_date': datetime.now().date(),
                'is_lhdn_pos_retail_combine_invoice': True,
                'state': 'draft'})

            todays_lhdn_retails_invoice.message_post(body="This Invoice is created for the Combine the pos order's Invocies")

        lines_list = []
        for order in res:
            pos_orders_id = self.env['pos.order'].browse(order.get('id'))
            if not pos_orders_id.partner_id:
                # pos_orders_id._create_order_picking()
                invoices_vals = pos_orders_id._prepare_invoice_vals()
                for line in invoices_vals.get('invoice_line_ids'):
                    line[2].update({'move_id':todays_lhdn_retails_invoice.id})
                    lines_list.append(line[2])
                todays_lhdn_retails_invoice.pos_order_ids = [(4, pos_orders_id.id)]
        self.env['account.move.line'].create(lines_list)
        return res
