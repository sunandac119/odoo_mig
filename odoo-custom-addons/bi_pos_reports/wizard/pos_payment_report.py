# -*- coding: utf-8 -*-
# Part of BrowseInfo. See LICENSE file for full copyright and licensing details.

from datetime import datetime,timedelta
from dateutil.relativedelta import relativedelta
from odoo import api, fields, models, _
from odoo.exceptions import Warning
import itertools

class posPaymentReport(models.AbstractModel):

	_name='report.bi_pos_reports.report_pos_payment'	
	_description ="POS Payment Report"
	
	def _get_report_values(self, docids, data=None,sessions=False):
		""" Serialise the orders of the day information

		params: pos_payment_rec.start_dt, pos_payment_rec.end_dt string representing the datetime of order
		"""
	  
		Report = self.env['ir.actions.report']
		start_dt = fields.Date('Start Date', required = True)
		end_dt = fields.Date('End Date', required = True)
		orders = self.env['pos.order'].search([
				('date_order', '>=', start_dt),
				('date_order', '<=', end_dt),
				('state', 'in', ['paid','invoiced','done']),
			])
		st_line_ids = self.env["pos.payment"].search([('pos_order_id', 'in', orders.ids)]).ids
		if st_line_ids:
			self.env.cr.execute("""
				SELECT ppm.name, sum(amount) total
				FROM pos_payment AS pp,
					pos_payment_method AS ppm
				WHERE  pp.payment_method_id = ppm.id 
					AND pp.id IN %s 
				GROUP BY ppm.name
			""", (tuple(st_line_ids),))
			payments = self.env.cr.dictfetchall()
		else:
			payments = []	
				
				
		return {
			'start_dt' : start_dt,
			'end_dt' : end_dt,
			'payments': payments,
		}
	

	

# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:
