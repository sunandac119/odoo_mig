# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.
import hashlib
import json

from odoo import api, models, fields, _
from odoo.http import request
from odoo.tools import ustr


class PosConfig(models.Model):
    _inherit = 'pos.config'

    # branch_ids = fields.Many2many('res.branch', string='branches')
    branch_id = fields.Many2one('res.branch', string='Branch', help='The default branch for this user.',
                                context={'user_preference': True},  default=lambda self: self.env.user.branch_id.id)

    # def open_ui(self):
    #     print("\n\n open_ui:::", self, self.id, )
    #     print("open_ui : brnach oid:", self.env.branch)
    #     """Open the pos interface with config_id as an extra argument.
    #
    #     In vanilla PoS each user can only have one active session, therefore it was not needed to pass the config_id
    #     on opening a session. It is also possible to login to sessions created by other users.
    #
    #     :returns: dict
    #     """
    #     self.ensure_one()
    #     # check all constraints, raises if any is not met
    #     self._validate_fields(set(self._fields) - {"cash_control"})
    #     return {
    #         'type': 'ir.actions.act_url',
    #         'url': '/pos/web?config_id=%d?branch_id=%s' %  default=lambda self: self.env.user.branch_id.id,
    #         'target': 'self',
    #     }