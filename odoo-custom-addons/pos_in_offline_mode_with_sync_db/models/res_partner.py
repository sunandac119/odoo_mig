from odoo import api, fields, models


class ResPartner(models.Model):
    _inherit = 'res.partner'

    is_synced_with_server = fields.Boolean(string="Is Synced with server?",default=False)
    remote_server_db_id = fields.Integer(string="Remote Server DB Id")