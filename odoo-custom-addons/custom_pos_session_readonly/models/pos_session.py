from lxml import etree
from odoo import models, api

class PosSession(models.Model):
    _inherit = 'pos.session'

    @api.model
    def fields_view_get(self, view_id=None, view_type='form', toolbar=False, submenu=False):
        res = super(PosSession, self).fields_view_get(view_id=view_id, view_type=view_type, toolbar=toolbar, submenu=submenu)
        user = self.env.user
        # Check if the view is 'form' and the user is NOT in the Accounting/Advisor group
        if view_type == 'form' and not user.has_group('account.group_account_manager'):
            doc = etree.XML(res['arch'])
            # Find the cash_register_difference field and make it read-only
            for node in doc.xpath("//field[@name='cash_register_difference']"):
                node.set('readonly', '1')
            res['arch'] = etree.tostring(doc, encoding='unicode')
        return res
