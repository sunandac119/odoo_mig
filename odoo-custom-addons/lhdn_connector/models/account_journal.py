from odoo import api, fields, models
class AccountJournal(models.Model):
    _inherit = 'account.journal'

    not_required_e_invoice = fields.Boolean(string="Not Required e-Invoice?",default=False)

