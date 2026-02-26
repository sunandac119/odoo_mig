# -*- coding: utf-8 -*-

from odoo import fields, models, _

class ResCompany(models.Model):
   _inherit = 'res.company'

   def action_subsidiary_coa(self):
       action = {
           'name': _("Chart of Accounts"),
           'view_mode': 'tree',
           'type': 'ir.actions.act_window',
           'res_model': 'account.account',
           'domain': [('company_id', '=', self.parent_id.id)],
       }
       return action


