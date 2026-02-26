from odoo import api, fields, models


class ResPartner(models.Model):
    _inherit = 'res.partner'

    external_system_db_id = fields.Char('External System DB Id')
    # chain_chon_ss_db_id = fields.Integer('External System DB Id')