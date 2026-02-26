# -*- coding: utf-8 -*-


from itertools import groupby

from odoo import api, fields, models, SUPERUSER_ID, _
from odoo.exceptions import AccessError, UserError, ValidationError
from odoo.tools import float_is_zero, float_compare


class SaleOrder(models.Model):
    _inherit = "sale.order"

    branch_id = fields.Many2one('res.branch', string='Branch Name', help='The default branch for this user.',
                                context={'user_preference': True}, default=lambda self: self.env.user.branch_id.id)

    # def write(self, values):
    #     print("\nwrite:....:", values, self)
    #     print("bnew:,", self.picking_ids)
    #     if values.get('procurement_group_id'):
    #         procu = self.env['procurement.group'].sudo().search([('id', '=', int(values['procurement_group_id']))])
    #         for record in procu:
    #             print("record:", record, record.name, record.sale_id)
    #
    #             procu.sudo().write({'branch_id': self.branch_id})
    #
    #     if values.get('order_line') and self.state == 'sale':
    #         for order in self:
    #             pre_order_line_qty = {order_line: order_line.product_uom_qty for order_line in
    #                                   order.mapped('order_line') if not order_line.is_expense}
    #
    #     if values.get('partner_shipping_id'):
    #         new_partner = self.env['res.partner'].browse(values.get('partner_shipping_id'))
    #         for record in self:
    #             picking = record.mapped('picking_ids').filtered(lambda x: x.state not in ('done', 'cancel'))
    #             addresses = (record.partner_shipping_id.display_name, new_partner.display_name)
    #             message = _("""The delivery address has been changed on the Sales Order<br/>
    #                        From <strong>"%s"</strong> To <strong>"%s"</strong>,
    #                        You should probably update the partner on this document.""") % addresses
    #             picking.activity_schedule('mail.mail_activity_data_warning', note=message, user_id=self.env.user.id)
    #     print("values:,,.:", values)
    #     res = super(SaleOrder, self).write(values)
    #     if values.get('order_line') and self.state == 'sale':
    #         for order in self:
    #             to_log = {}
    #             for order_line in order.order_line:
    #                 if float_compare(order_line.product_uom_qty, pre_order_line_qty.get(order_line, 0.0),
    #                                  order_line.product_uom.rounding) < 0:
    #                     to_log[order_line] = (order_line.product_uom_qty, pre_order_line_qty.get(order_line, 0.0))
    #             if to_log:
    #                 documents = self.env['stock.picking']._log_activity_get_documents(to_log, 'move_ids', 'UP')
    #                 documents = {k: v for k, v in documents.items() if k[0].state != 'cancel'}
    #                 order._log_decrease_ordered_quantity(documents)
    #     print("res...:", res)
    #     return res

    def _create_invoices(self, grouped=False, final=False):
        """
        Create the invoice associated to the SO.
        :param grouped: if True, invoices are grouped by SO id. If False, invoices are grouped by
                        (partner_invoice_id, currency)
        :param final: if True, refunds will be generated if necessary
        :returns: list of created invoices
        """
        if not self.env['account.move'].check_access_rights('create', False):
            try:
                self.check_access_rights('write')
                self.check_access_rule('write')
            except AccessError:
                return self.env['account.move']

        # 1) Create invoices.
        invoice_vals_list = []
        for order in self:

            invoice_vals = order._prepare_invoice()
            invoiceable_lines = order._get_invoiceable_lines(final)

            if not invoiceable_lines and not invoice_vals['invoice_line_ids']:
                raise UserError(_('There is no invoiceable line. If a product has a Delivered quantities invoicing policy, please make sure that a quantity has been delivered.'))

            # there is a chance the invoice_vals['invoice_line_ids'] already contains data when
            # another module extends the method `_prepare_invoice()`. Therefore, instead of
            # replacing the invoice_vals['invoice_line_ids'], we append invoiceable lines into it
            invoice_vals['invoice_line_ids'] += [
                (0, 0, line._prepare_invoice_line())
                for line in invoiceable_lines
            ]

            invoice_vals_list.append(invoice_vals)

        if not invoice_vals_list:
            raise UserError(_(
                'There is no invoiceable line. If a product has a Delivered quantities invoicing policy, please make sure that a quantity has been delivered.'))

        # 2) Manage 'grouped' parameter: group by (partner_id, currency_id).
        if not grouped:
            new_invoice_vals_list = []
            invoice_grouping_keys = self._get_invoice_grouping_keys()
            for grouping_keys, invoices in groupby(invoice_vals_list, key=lambda x: [x.get(grouping_key) for grouping_key in invoice_grouping_keys]):
                origins = set()
                payment_refs = set()
                refs = set()
                ref_invoice_vals = None
                for invoice_vals in invoices:
                    if not ref_invoice_vals:
                        ref_invoice_vals = invoice_vals
                    else:
                        ref_invoice_vals['invoice_line_ids'] += invoice_vals['invoice_line_ids']
                    origins.add(invoice_vals['invoice_origin'])
                    payment_refs.add(invoice_vals['payment_reference'])
                    refs.add(invoice_vals['ref'])
                ref_invoice_vals.update({
                    'ref': ', '.join(refs)[:2000],
                    'invoice_origin': ', '.join(origins),
                    'payment_reference': len(payment_refs) == 1 and payment_refs.pop() or False,
                })
                new_invoice_vals_list.append(ref_invoice_vals)
            invoice_vals_list = new_invoice_vals_list

        # 3) Create invoices.

        # As part of the invoice creation, we make sure the sequence of multiple SO do not interfere
        # in a single invoice. Example:
        # SO 1:
        # - Section A (sequence: 10)
        # - Product A (sequence: 11)
        # SO 2:
        # - Section B (sequence: 10)
        # - Product B (sequence: 11)
        #
        # If SO 1 & 2 are grouped in the same invoice, the result will be:
        # - Section A (sequence: 10)
        # - Section B (sequence: 10)
        # - Product A (sequence: 11)
        # - Product B (sequence: 11)
        #
        # Resequencing should be safe, however we resequence only if there are less invoices than
        # orders, meaning a grouping might have been done. This could also mean that only a part
        # of the selected SO are invoiceable, but resequencing in this case shouldn't be an issue.
        if len(invoice_vals_list) < len(self):
            SaleOrderLine = self.env['sale.order.line']
            for invoice in invoice_vals_list:
                sequence = 1
                for line in invoice['invoice_line_ids']:
                    line[2]['sequence'] = SaleOrderLine._get_invoice_line_sequence(new=sequence, old=line[2]['sequence'])
                    sequence += 1

        # Manage the creation of invoices in sudo because a salesperson must be able to generate an invoice from a
        # sale order without "billing" access rights. However, he should not be able to create an invoice from scratch.
        moves = self.env['account.move'].sudo().with_context(default_type='out_invoice').create(invoice_vals_list)
        moves.write({'branch_id': self.branch_id})
        for loop in moves.line_ids:
            loop.sudo().write({'branch_id': self.branch_id})

        # 4) Some moves might actually be refunds: convert them if the total amount is negative
        # We do this after the moves have been created since we need taxes, etc. to know if the total
        # is actually negative or not
        if final:
            moves.sudo().filtered(lambda m: m.amount_total < 0).action_switch_invoice_into_refund_credit_note()
        for move in moves:
            move.message_post_with_view('mail.message_origin_link',
                values={'self': move, 'origin': move.line_ids.mapped('sale_line_ids.order_id')},
                subtype_id=self.env.ref('mail.mt_note').id
            )
        return moves
