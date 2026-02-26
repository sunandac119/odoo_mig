# -*- coding: utf-8 -*-

from odoo import api, fields, models
import datetime


class StockPicking(models.Model):
    _inherit = "stock.picking"

    branch_id = fields.Many2one("res.branch", string='Branch', help='The default branch for this user.',
                                context={'user_preference': True}, default=lambda self: self.env.user.branch_id.id)
    #
    # branch_id_del = fields.Many2one(related="group_id.branch_id", string='Branch', help='The default branch for this user.',
    #                             context={'user_preference': True},  default=lambda self: self.env.branch)


class ProcurementGroup(models.Model):
    _inherit = 'procurement.group'

    branch_id = fields.Many2one('res.branch', 'Branch',  default=lambda self: self.env.user.branch_id.id)

