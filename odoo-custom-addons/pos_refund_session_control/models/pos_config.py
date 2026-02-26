from odoo import models, fields

class PosConfig(models.Model):
    _inherit = 'pos.config'

    allow_order_refund = fields.Boolean("Allow POS Order Refund", default=True)
