# -*- coding: utf-8 -*-
##############################################################################
#
#    TL Technology
#    Copyright (C) 2019 ­TODAY TL Technology (<https://www.posodoo.com>).
#    Odoo Proprietary License v1.0 along with this program.
#
##############################################################################
from odoo import api, fields, models, _

class PosConfig(models.Model):
    _inherit = "pos.config"

    active_design_layout = fields.Boolean('Active Design Layout')
    load_design_of_pos_config_id = fields.Many2one('pos.config', 'Load Template Design Of POS')