# -*- coding: utf-8 -*-
# Part of Browseinfo. See LICENSE file for full copyright and licensing details.

from odoo import api, fields, models,_
from odoo.exceptions import UserError


class ResConfigSettings(models.TransientModel):
    _inherit = 'res.config.settings'

    account_first_approval = fields.Boolean("First Approval")
    account_first_approval_minimum_amount = fields.Float("Minimum Amount")
    account_second_approval = fields.Boolean("Second Approval")
    account_second_approval_minimum_amount = fields.Float("Minimum Amount")

    approval_vendor = fields.Boolean("Approval for Vendor Payment")
    approval_customer = fields.Boolean("Approval for Customer Payment")

    @api.model
    def default_get(self, fields):
        settings = super(ResConfigSettings, self).default_get(fields)
        settings.update(self.get_account_payment_approval_config(fields))
        return settings

    @api.model
    def get_account_payment_approval_config(self, fields):
        account_payment_config = \
                    self.env.ref('bi_payment_double_approval.account_payment_approval_config_data')
        return {
            'account_first_approval': account_payment_config.account_first_approval,
            'account_first_approval_minimum_amount': account_payment_config.account_first_approval_minimum_amount,
            'account_second_approval': account_payment_config.account_second_approval,
            'account_second_approval_minimum_amount': account_payment_config.account_second_approval_minimum_amount,
            'approval_vendor':account_payment_config.approval_vendor,
            'approval_customer':account_payment_config.approval_customer,
        }

    
    def set_values(self):
        super(ResConfigSettings, self).set_values()
        account_payment_config = \
                    self.env.ref('bi_payment_double_approval.account_payment_approval_config_data')
        vals = {
            'account_first_approval': self.account_first_approval,
            'account_first_approval_minimum_amount': self.account_first_approval_minimum_amount,
            'account_second_approval': self.account_second_approval,
            'account_second_approval_minimum_amount': self.account_second_approval_minimum_amount,
            'approval_vendor':self.approval_vendor,
            'approval_customer':self.approval_customer,
        }
        account_payment_config.write(vals)


class AccountPaymentApprovalConfiguration(models.Model):
    _name = 'account.payment.approval.config'
    _description = 'Account Payment Approval Configuration'

    account_first_approval = fields.Boolean("First Approval")
    account_first_approval_minimum_amount = fields.Float("Minimum Amount")
    account_second_approval = fields.Boolean("Second Approval")
    account_second_approval_minimum_amount = fields.Float("Minimum Amount")

    approval_vendor = fields.Boolean("Approval for Vendor Payment")
    approval_customer = fields.Boolean("Approval for Customer Payment")

    @api.constrains('account_second_approval_minimum_amount')
    def warrning_seccond_approval(self) :
        if self.account_first_approval == True and self.account_second_approval == True :
            if self.account_first_approval_minimum_amount > self.account_second_approval_minimum_amount :
                raise    UserError(_('Second approval amount must be greater than First approval amount'))

