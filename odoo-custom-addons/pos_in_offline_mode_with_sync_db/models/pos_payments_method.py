from odoo import api, fields, models


class PosPaymentsMethods(models.Model):
    _inherit = 'pos.payment.method'

    is_synced_with_server = fields.Boolean(string="Is Synced with server?",default=False)
    remote_server_db_id = fields.Integer(string="Remote Server DB Id")
