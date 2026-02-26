from odoo import fields, models

class PosConfig(models.Model):
    _inherit = 'pos.config'

    allow_pos_return = fields.Boolean(string="Allow POS Returns")
