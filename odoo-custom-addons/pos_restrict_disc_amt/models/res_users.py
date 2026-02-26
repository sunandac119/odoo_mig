from odoo import models, fields

class ResUsers(models.Model):
    _inherit = 'res.users'

    allow_pos_discount = fields.Boolean(string='Allow POS Discount')
    allow_pos_price = fields.Boolean(string='Allow POS Price Change')
