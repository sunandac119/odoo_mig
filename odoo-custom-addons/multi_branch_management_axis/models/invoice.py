# -*- coding: utf-8 -*-

from odoo import api, fields, models, _
from odoo.exceptions import UserError


class Account(models.Model):
    _inherit = "account.move"

    @api.onchange('partner_id')
    def _get_branch_id(self):
        # print("my onchabge:...:", self.env.branch)
        pass
    #     print("hi inside onchange brnac\n---->self:", self)
    #     print("self: opartner :", self.partner_id, self.partner_id.name)
    #     print("self: Company :", self.env.company, self.env.companies)
    #     print("self branch:.",self.env.context, ':--->:', self.branch_id)
    #
    #     print("self user::..:", self, self.env.user, self.env.user.name, ':br:', self.env.user.branch_id, self.env.user.company_id)
    #
    #     print("\n b-brnach:", self.env.context.get('allowed_branch_ids'))
    #     branch_list =  self.env.context.get('allowed_branch_ids')
    #     branch_id = self.env['res.branch'].sudo().search([('id', 'in', branch_list)])
    #     print("branvch_id ....3:..:", branch_id)
    #     # return branch_id
    #
    #     print(":\n\n\n", self, self.env)
    #
    #     print("\n\n-->:", dir(self.env))
    #     print("\n\n\-->", self.env.values, '\n')
    #
    #     print("\n dinal brnach:..:", self.env.branch)
    #     pass
    # branch_id = fields.Many2one('res.branch', string='Branch', help='The default branch for this user.',
    #                             context={'user_preference': True}, default=_get_branch_id)

    branch_id = fields.Many2one('res.branch', string='Branch', help='The default branch for this user.',
                                context={'user_preference': True},  default=lambda self: self.env.user.branch_id.id)


class AccountMoveLine(models.Model):
    _inherit = "account.move.line"

    branch_id = fields.Many2one('res.branch', string='Branch', help='The default branch for this user.',
                                context={'user_preference': True},  default=lambda self:  self.env.user.branch_id.id)


class AccountPayment(models.Model):
    _inherit = "account.payment"

    branch_id = fields.Many2one('res.branch', string='Branch', help='The default branch for this user.',
                                context={'user_preference': True}, default=lambda self:  self.env.user.branch_id.id)


# class PaymentRegister(models.TransientModel):
#     _inherit = 'account.payment.register'
# 
#     def _prepare_payment_vals(self, invoices):
#         print("\n\n\n ----> Self : _prepare_payment_vals:", self, invoices, self.branch_id)
#         values = super(PaymentRegister, self)._prepare_payment_vals(invoices)
#         print(" calval:", values)
#         values.updae({
# 
#             'branch_id': self.branch_id.id
#         })
#         print("afte calval:", values)
#         return values

class SaleAdvancePaymentInv(models.TransientModel):
    _inherit = "sale.advance.payment.inv"
    _description = "Sales Advance Payment Invoice"

    def _create_invoice(self, order, so_line, amount):
        if (self.advance_payment_method == 'percentage' and self.amount <= 0.00) or (self.advance_payment_method == 'fixed' and self.fixed_amount <= 0.00):
            raise UserError(_('The value of the down payment amount must be positive.'))

        amount, name = self._get_advance_details(order)

        invoice_vals = self._prepare_invoice_values(order, name, amount, so_line)
        if order.fiscal_position_id:
            invoice_vals['fiscal_position_id'] = order.fiscal_position_id.id
        invoice_vals['branch_id'] = order.branch_id
        invoice = self.env['account.move'].sudo().create(invoice_vals).with_user(self.env.uid)

        for loop in invoice.line_ids:
            loop.sudo().write({'branch_id': order.branch_id})

        invoice.message_post_with_view('mail.message_origin_link',
                    values={'self': invoice, 'origin': order},
                    subtype_id=self.env.ref('mail.mt_note').id)
        return invoice


class AccountReconcileModel(models.Model):
    _inherit = "account.reconcile.model"

    branch_id = fields.Many2one('res.branch', string='Branch', help='The default branch for this user.',
                                context={'user_preference': True}, default=lambda self:  self.env.user.branch_id.id)
