from odoo import models, api
from datetime import datetime

class AccountMove(models.Model):
    _inherit = 'account.move'

    @api.model
    def create(self, vals):
        if vals.get('move_type') == 'out_invoice' and not vals.get('name'):
            today = datetime.today()
            yymm = today.strftime('%y%m')
            prefix = f'BRPINV{yymm}'
            seq_code = f'custom.invoice.{yymm}'

            seq = self.env['ir.sequence'].sudo().search([('code', '=', seq_code)], limit=1)
            if not seq:
                seq = self.env['ir.sequence'].sudo().create({
                    'name': f'Invoice {yymm}',
                    'code': seq_code,
                    'prefix': prefix,
                    'padding': 4,
                    'number_next': 1,
                    'number_increment': 1,
                    'implementation': 'no_gap',
                })

            vals['name'] = self.env['ir.sequence'].next_by_code(seq_code)

        return super(AccountMove, self).create(vals)
