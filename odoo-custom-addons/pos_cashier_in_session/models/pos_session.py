from odoo import models, fields, api

class PosSession(models.Model):
    _inherit = 'pos.session'

    cashier_id = fields.Many2one(
        'hr.employee',
        string='Cashier',
        compute='_compute_cashier_id',
        store=False,
        readonly=False
    )

    @api.depends('order_ids')
    def _compute_cashier_id(self):
        for session in self:
            latest_order = session.order_ids.filtered(lambda o: o.employee_id).sorted('date_order', reverse=True)[:1]
            session.cashier_id = latest_order.employee_id if latest_order else False



