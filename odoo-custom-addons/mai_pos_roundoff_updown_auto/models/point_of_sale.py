from odoo import models, fields, api, tools, _
from datetime import datetime, timedelta
import time
from pytz import timezone
import logging

_logger = logging.getLogger(__name__)

class PosConfig(models.Model):
    _inherit = 'pos.config'

    enable_rounding = fields.Boolean("Rounding Total")
    rounding_options = fields.Selection([("digits", 'Digits'), ('points','Points'),], string='Rounding Options', default='digits')
    rounding_journal_id = fields.Many2one('pos.payment.method',"Rounding Payment Method")

class PosOrder(models.Model):
    _inherit = 'pos.order'

    is_rounding = fields.Boolean("Is Rounding")
    rounding_option = fields.Char("Rounding Option")
    rounding = fields.Float(string='Rounding', digits=0)

    def _order_fields(self,ui_order):
        res = super(PosOrder, self)._order_fields(ui_order)
        res.update({
            'is_rounding':          ui_order.get('is_rounding') or False,
            'rounding_option':      ui_order.get('rounding_option') or False,
            'rounding':             ui_order.get('rounding') or False,
        })
        return res

    # def create(self, values):
    #     order_id = super(PosOrder, self).create(values)
    #     rounding_journal_id = order_id.session_id.config_id.rounding_journal_id
    #     if order_id.rounding != 0:
    #         if rounding_journal_id:
    #             self.env['pos.make.payment'].with_context({"active_ids": [order_id.id], "active_id": order_id.id}).create({'payment_method_id': rounding_journal_id.id,
    #                 'amount': order_id.rounding * -1}).check()
                # order_id.add_payment({
                #     'name': _('Rounding'),
                #     'pos_order_id': order_id.id,
                #     'amount':order_id.rounding * -1,
                #     'payment_date': time.strftime('%Y-%m-%d %H:%M:%S'),
                #     'payment_method_id': rounding_journal_id.id,
                # })
        # return order_id

    @api.model
    def _process_order(self, order, draft, existing_order):
        order_id = super(PosOrder, self)._process_order(order, draft, existing_order)
        order_id = self.browse(order_id)
        rounding_journal_id = order_id.session_id.config_id.rounding_journal_id
        if order_id.rounding != 0:
            if rounding_journal_id:
                self.env['pos.make.payment'].with_context({"active_ids": [order_id.id], "active_id": order_id.id}).create({'payment_method_id': rounding_journal_id.id,
                    'amount': order_id.rounding * -1}).check()
        return order_id.id

    