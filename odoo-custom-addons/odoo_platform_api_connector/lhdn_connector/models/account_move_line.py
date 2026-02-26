from odoo import api, fields, models


class AccountMoveLine(models.Model):
    _inherit = 'account.move.line'

    older_invoice_line_id = fields.Many2one('account.move.line',string="Older Invoice Line Number(Before Combine)")
