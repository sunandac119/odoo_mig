# -*- coding: utf-8 -*-
from odoo import fields, models, api, _


class ResUsers(models.Model):
    _inherit = 'res.users'

    pw_disable_payment = fields.Boolean('Disable Payment', default=False, copy=False)
    pw_disable_discount = fields.Boolean('Disable Discount', default=False, copy=False)
    pw_disable_qty = fields.Boolean('Disable Qty', default=False, copy=False)
    pw_disable_price = fields.Boolean('Disable Edit Price', default=False, copy=False)
    pw_disable_remove_orderline = fields.Boolean('Disable Remove Order Line', default=False, copy=False)
