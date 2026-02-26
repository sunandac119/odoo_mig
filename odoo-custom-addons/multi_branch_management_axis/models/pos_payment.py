# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.
import hashlib
import json

from odoo import api, models, fields, _
from odoo.http import request
from odoo.tools import ustr


class PosPayment(models.Model):
    _inherit = 'pos.payment'

    branch_id = fields.Many2one('res.branch', string='Branch', help='The default branch for this user.',
                                context={'user_preference': True},  default=lambda self: self.env.user.branch_id.id)


class PosPaymentMethod(models.Model):

    _inherit = 'pos.payment.method'

    branch_id = fields.Many2one('res.branch', string='Branch', help='The default branch for this user.',
                                context={'user_preference': True},  default=lambda self: self.env.user.branch_id.id)
