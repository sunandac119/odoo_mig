# -*- coding: utf-8 -*-

from odoo import api, fields, models , tools


class PosOrder(models.Model):
    _inherit = 'pos.order'

    def send_receipt_by_email(self):
        self.ensure_one()
        lang = self.env.context.get('lang')
        template = self.env.ref('bi_pos_receipt_in_backend.pos_sale_order_email_template')
        pos_order_id = self.env['pos.order'].sudo().browse(self.id)
        if template.lang:
            lang = template._render_lang(self.ids)[self.id]
        ctx = {
            'default_model': 'pos.order',
            'default_res_id': pos_order_id.id,
            'default_use_template': bool(template.id),
            'default_template_id': template.id,
            'default_composition_mode': 'comment',
            'mark_so_as_sent': True,
            'force_email': True,
        }
        return {
            'type': 'ir.actions.act_window',
            'view_mode': 'form',
            'res_model': 'mail.compose.message',
            'views': [(False, 'form')],
            'view_id': False,
            'target': 'new',
            'context': ctx,
        }




