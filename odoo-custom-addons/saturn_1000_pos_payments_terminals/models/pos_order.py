from odoo import api, fields, models
class PosOrder(models.Model):
    _inherit = 'pos.order'

    transaction_id = fields.Char(string="Transaction Id")
    approval_code= fields.Char(string="Approval Code")
    payment_terminal_inv_no= fields.Char(string="Payments Terminal INV No")
    trace_no= fields.Char(string="Trace No")
    payments_terminal_id= fields.Char(string="Payments Terminal Id")
    retrival_ref_no= fields.Char(string="Retrival Ref No")


    def _order_fields(self, ui_order):
        order_fields = super(PosOrder, self)._order_fields(ui_order)
        order_fields['transaction_id'] = ui_order.get('transaction_id')
        order_fields['approval_code'] = ui_order.get('approval_code')
        order_fields['payment_terminal_inv_no'] = ui_order.get('payment_terminal_inv_no')
        order_fields['trace_no'] = ui_order.get('trace_no')
        order_fields['payments_terminal_id'] = ui_order.get('payments_terminal_id')
        order_fields['retrival_ref_no'] = ui_order.get('retrival_ref_no')
        return order_fields