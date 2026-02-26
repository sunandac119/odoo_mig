from odoo import api, fields, models


class AccountMove(models.Model):
    _inherit = 'account.move'

    external_system_db_id = fields.Char("External System DB Id")
    external_system_invoice_number = fields.Char("External System Invoice Number")
    # chain_chon_ss_db_id = fields.Integer('External System DB Id')