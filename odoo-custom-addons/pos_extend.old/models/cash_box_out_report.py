from datetime import datetime, timedelta
from odoo.tools.misc import DEFAULT_SERVER_DATETIME_FORMAT
from odoo import models, fields, api, _



class CashBoxOut(models.TransientModel):
	_inherit = 'cash.box.out'

	def generate_cash_out_report(self):
		context = dict(self._context or {})
		active_model = context.get('active_model', False)
		active_ids = context.get('active_ids', [])

		cash_box_list = []
		subtotal = 0.0
		value_total = 0.0
		qty_total = 0.0
		for rec in self.cashbox_lines_ids:
			cash_dict = {
				'value': round(rec.coin_value, 2),
				'code': round(rec.number,2),
				'subtotal': round(rec.subtotal,2)
			}
			subtotal += rec.subtotal
			value_total += rec.coin_value
			qty_total += rec.number
			cash_box_list.append(cash_dict)

		data = {
			'report_name':"CASH BALANCE",
			'session_ids':active_ids,
			'cash_box_list':cash_box_list,
			'value_total':value_total,
			'qty_total':qty_total,
			'total':subtotal
			}
		return self.env.ref('pos_extend.action_cash_box_out_report_print').report_action([], data=data)

	def generate_cash_out_report_1(self):
		context = dict(self._context or {})
		active_model = context.get('active_model', False)
		active_ids = context.get('active_ids', [])

		cash_box_list = []
		subtotal = 0.0
		value_total = 0.0
		qty_total = 0.0
		for rec in self.cashbox_lines_ids:
			cash_dict = {
				'value': round(rec.coin_value, 2),
				'code': round(rec.number,2),
				'subtotal': round(rec.subtotal,2)
			}
			subtotal += rec.subtotal
			value_total += rec.coin_value
			qty_total += rec.number
			cash_box_list.append(cash_dict)

		data = {
			'report_name':"DRAWER",
			'session_ids':active_ids,
			'cash_box_list':cash_box_list,
			'value_total':value_total,
			'qty_total':qty_total,
			'total':subtotal
			}
		return self.env.ref('pos_extend.action_cash_box_out_report_1_print').report_action([], data=data)

		

class CashBoxOutReport(models.AbstractModel):
    _name = 'report.pos_extend.report_cash_out'
    _description = 'Cash Box Out Report'

    def _get_report_values(self, docids, data=None):
        data = dict(data or {})
        sessions = self.env['pos.session'].browse(data['session_ids'])
        company = sessions.company_id

        cash_box_list = data['cash_box_list']
        total = data['total']
        session_time = fields.Datetime.to_string(sessions.start_at)
        formatted_session_time = ''
        if session_time:
            formatted_session_time = (datetime.strptime(session_time, DEFAULT_SERVER_DATETIME_FORMAT) + timedelta(hours=8)).strftime('%d-%m-%Y %H:%M')

        data.update({
            'cash_box_list': cash_box_list,
            'total': total,
            'company_name': company.name,
            'session': sessions.name,
            'cashier_name': sessions.user_id.name,
            'counter_name': sessions.config_id.name,
            'session_time': session_time,
            'formatted_session_time': formatted_session_time,
        })

        return data

