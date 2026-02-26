from odoo import fields, models, api, _

class AccountAccount(models.Model):
    _inherit = 'account.account'

    active = fields.Boolean(default=True)
    special_user_type_id = fields.Many2one('account.account.type', string='Special Type')

    def action_import_coa(self):
        if self.env.context.get('default_company_id'):
            for rec in self:
                exist_account = self.env['account.account'].sudo().search([
                    ('company_id','=',self.env.context.get('default_company_id')),
                    ('name','=',rec.name),
                ])
                if not exist_account:
                    account = self.env['account.account'].sudo().create({
                        'name' : rec.name,
                        'code' : rec.code,
                        'user_type_id' : rec.user_type_id.id,
                        'company_id' : self.env.context.get('default_company_id')
                    })

            #self = self.with_context(allowed_company_ids=[self.env.context.get('default_company_id')])
            #self = self.with_context(active_domain=[['company_id', '=', self.env.context.get('default_company_id')]])

            return {
                'type': 'ir.actions.client',
                'name': 'Chart of Accounts',
                'tag': 'reload',
                'params': {'menu_id': self.env.ref('account.menu_action_account_form').id},
                # 'context': {'company_ids': [self.env.context.get('default_company_id')],'allowed_company_ids':[self.env.context.get('default_company_id')]},
            }
            # return {
            #     'name': _("Company"),
            #     'view_mode': 'form',
            #     'views': [(False, 'form')],
            #     'type': 'ir.actions.act_window',
            #     'res_model': 'res.company',
            #     'res_id': self.env.context.get('default_company_id'),
            #     'target': 'current',
            # }
            # return {
            #     'type': 'ir.actions.client',
            #     'tag': 'display_notification',
            #     'params': {
            #         'type': 'success',
            #         'message': _("Chart of Accounts Created Successfully!"),
            #         'next': {'type': 'ir.actions.act_window_close'},
            #         'sticky': True,
            #     }
            # }


