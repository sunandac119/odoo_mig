from odoo import models, fields

class POSManagerLog(models.Model):
    _name = 'pos.manager.log'
    _description = 'POS Manager Validation Log'
    _order = 'create_date desc'

    user_id = fields.Many2one('res.users', string='Validated By', required=True)
    action = fields.Char(string='Action', required=True)
    create_date = fields.Datetime(string='Validated At', readonly=True)