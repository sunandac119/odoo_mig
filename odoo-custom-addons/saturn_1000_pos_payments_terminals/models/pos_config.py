# -*- coding: utf-8 -*-

from functools import partial

from odoo import models, fields


class PosConfig(models.Model):
    _inherit = 'pos.config'


    local_pc_tunneling_url = fields.Char(string="Local Systems Tunnelings URL")