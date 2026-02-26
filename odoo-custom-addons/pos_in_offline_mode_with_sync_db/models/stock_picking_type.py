from odoo import api, fields, models


class StockPickingType(models.Model):
    _inherit = 'stock.picking.type'

    is_synced_with_server = fields.Boolean(string="Is Synced with server?",default=False)
    remote_server_db_id = fields.Integer(string="Remote Server DB Id")