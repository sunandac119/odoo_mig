from odoo import models, api

class PosOrder(models.Model):
    _inherit = 'pos.order'

    @api.model
    def get_orders_by_branch(self):
        user = self.env.user
        if not hasattr(user, 'branch_id') or not user.branch_id:
            return []
        orders = self.search([
            ('company_id', '=', user.company_id.id),
            ('session_id.config_id.branch_id', '=', user.branch_id.id)
        ], limit=1000)
        return [{
            'id': o.id,
            'name': o.name,
            'partner_id': o.partner_id.id if o.partner_id else False,
            'date_order': o.date_order,
            'amount_total': o.amount_total,
            'amount_tax': o.amount_tax,
            'pos_reference': o.pos_reference,
            'return_ref': o.return_ref,
            'return_status': o.return_status,
        } for o in orders]