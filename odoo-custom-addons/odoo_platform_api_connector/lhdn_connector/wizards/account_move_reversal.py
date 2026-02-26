# -*- coding: utf-8 -*-
from odoo import models, fields, api
from odoo.tools.translate import _
from odoo.exceptions import UserError


class AccountMoveReversal(models.TransientModel):
    """
    Account move reversal wizard, it cancel an account move by reversing it.
    """
    _inherit = 'account.move.reversal'

    def refund_moves(self):
        res = super().refund_moves()
        if res.get('res_id') and self.move_ids[0].lhdn_uuid and self.move_ids[0].lhdn_invoice_status in ['validated','submitted']:
            credit_notes_id = self.env['account.move'].browse(res.get('res_id'))
            if credit_notes_id:
                credit_notes_id.origin_lhdn_uuid = self.move_ids[0].lhdn_uuid
        return res
