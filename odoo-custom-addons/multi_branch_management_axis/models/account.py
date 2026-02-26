# -*- coding: utf-8 -*-

from odoo import fields, models


class Account(models.Model):
    _inherit = 'account.account.type'

    activity_type = fields.Selection(
        [('operation_income', 'Operation-Income'),
         ('operation_expense', 'Operation-Expense'),
         ('operation_current_asset', 'Operation-Current Asset'),
         ('operation_current_liability', 'Operation-Current Liability'),
         ('investing', 'Investing'),
         ('financing', 'Financing')], string='Activity Type')

