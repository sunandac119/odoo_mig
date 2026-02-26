from odoo import models, fields, api, _
from odoo.exceptions import UserError

class PosOrder(models.Model):
    _inherit = "pos.order"

    def refund(self):
        self.ensure_one()
        config = self.session_id.config_id
        if not config.allow_order_refund:
            raise UserError(_("Refunds are disabled for POS '%s'.") % config.name)

        # Try to find an open session for this POS config
        session = self.env['pos.session'].search([
            ('state', '=', 'opened'),
            ('config_id', '=', config.id)
        ], limit=1)

        # If none, create a new one
        if not session:
            session = self.env['pos.session'].create({
                'user_id': self.env.uid,
                'config_id': config.id,
                'name': '%s - Return Session (%s)' % (config.name, fields.Datetime.now()),
                'start_at': fields.Datetime.now(),
            })
            session.opening_control_ids = [(0, 0, {
                'coin_value': 0,
                'number': 0,
                'subtotal': 0,
            })]
            session.action_pos_session_open()

        ctx = dict(self.env.context, do_not_check_negative_qty=True, active_id=session.id)
        return super(PosOrder, self.with_context(ctx)).refund()
