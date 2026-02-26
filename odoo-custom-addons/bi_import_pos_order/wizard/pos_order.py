# -*- coding: utf-8 -*-
# Part of BrowseInfo. See LICENSE file for full copyright and licensing details.

import time
import datetime
import tempfile
import binascii
import xlrd
import io,re
from odoo.tools import DEFAULT_SERVER_DATETIME_FORMAT, DEFAULT_SERVER_DATE_FORMAT
from datetime import date, datetime
from odoo.exceptions import UserError, RedirectWarning, ValidationError

from odoo import models, fields, exceptions, api, _
import logging

_logger = logging.getLogger(__name__)

try:
	import csv
except ImportError:
	_logger.debug('Cannot `import csv`.')
try:
	import cStringIO
except ImportError:
	_logger.debug('Cannot `import cStringIO`.')
try:
	import base64
except ImportError:
	_logger.debug('Cannot `import base64`.')


class pos_order(models.Model):
	_inherit = "pos.order"

	custom_name = fields.Char(string="Name")


class pos_order_line(models.Model):
	_inherit = "pos.order.line"


	def _compute_amount_line_all(self):
		self.ensure_one()
		fpos = self.order_id.fiscal_position_id
		tax_ids_after_fiscal_position = fpos.map_tax(self.tax_ids)
		price = self.price_unit * (1 - (self.discount or 0.0) / 100.0)
		taxes = tax_ids_after_fiscal_position.compute_all(price, self.order_id.pricelist_id.currency_id, self.qty, product=self.product_id, partner=self.order_id.partner_id)
		return {
			'price_subtotal_incl': taxes.get('total_included'),
			'price_subtotal': taxes.get('total_excluded'),
		}


class gen_pos_order(models.TransientModel):
	_name = "gen.pos.order"

	file_to_upload = fields.Binary('File')
	file_name = fields.Char()
	import_option = fields.Selection([('csv', 'CSV File'), ('xlsx', 'XLSX File')], string='Select', default='csv')
	order_option = fields.Selection([('draft', 'Draft'), ('confirm', 'Confirm')], string='Stage', default='draft')
	sequence_option = fields.Selection([('custom_seq', 'Custom Sequence'), ('default_seq', 'Default Sequence')],
									   string='Select Sequence', default='custom_seq')
	import_product_by = fields.Selection([('name', 'Name'), ('code', 'Code'), ('barcode', 'Barcode')],
										 string='Select Product By', default='name')
	create_customer = fields.Boolean(string='Create Customer')
	journal_enable = fields.Boolean()
	journal_id = fields.Many2one('pos.payment.method')

	@api.onchange('order_option')
	def _onchange_order_option(self):
		if self.order_option == 'draft':
			self.journal_enable = False
		else:
			self.journal_enable = True

	def find_session_id(self, session):
		if session:
			session_ids = self.env['pos.session'].search([('name', '=', session)])
			if session_ids:
				session_id = session_ids[0]
				return session_id
			else:
				raise ValidationError(_('Wrong Session %s') % session)
		else:
			raise ValidationError(_("Please fill 'Session' column in CSV or XLS file."))

	def find_partner(self, partner_name):
		partner_ids = self.env['res.partner'].search([('name', '=', partner_name)])
		if self.create_customer:
			if len(partner_ids) != 0:
				partner_id = partner_ids[0]
				return partner_id
			else:
				partner_data = {
					'name': partner_name,
				}
				if partner_data:
					new_data = self.env['res.partner'].sudo().create(partner_data)
					return new_data
		else:
			if len(partner_ids) != 0:
				partner_id = partner_ids[0]
				return partner_id
			else:
				raise ValidationError(_('Wrong Partner %s') % partner_name)

	def check_product(self, product):
		product_ids = self.env['product.product'].search([('name', '=', product)])
		if product_ids:
			product_id = product_ids[0]
			return product_id
		else:
			raise ValidationError(_('Wrong Product %s') % product)

	def check_product_code(self, product):
		product_ids = self.env['product.product'].search([('default_code', '=', product)])
		if product_ids:
			product_id = product_ids[0]
			return product_id
		else:
			raise ValidationError(_('Wrong Product %s') % product)

	def check_product_barcode(self, product):
		product_barcode = (product.split('.'))
		product_ids = self.env['product.product'].search([('barcode', '=', product_barcode[0])])
		if product_ids:
			product_id = product_ids[0]
			return product_id
		else:
			raise ValidationError(_('Wrong Product %s') % product)

	def find_sales_person(self, name):
		sals_person_obj = self.env['res.users']
		partner_search = sals_person_obj.search([('name', '=', name)])
		if partner_search:
			if len(partner_search) > 1:
				raise UserError(_('Multiple user found with the name "%s". Please specify a unique user name.') % name)
			return partner_search
		else:
			raise ValidationError(_('Not Valid Salesperson Name "%s"') % name)


	def find_receipt_number(self, name):
		if re.search('([0-9]|-){14}', name):
			return re.search('([0-9]|-){14}', name).group(0)
		else:
			raise ValidationError(_('Not Valid receipt number "%s", eg:- Order 00002-027-0001') % name)


	def make_pos(self, values, stage,sequence):
		pos_obj = self.env['pos.order']
		partner_id = self.find_partner(values.get('partner_id'))
		salesperson_id = self.find_sales_person(values.get('salesperson'))
		session_id = self.find_session_id(values.get('session'))
		receipt = self.find_receipt_number(values.get('receipt'))
		DATETIME_FORMAT = '%m/%d/%Y %H:%M:%S'
		try:
			i_date = datetime.strptime(values.get('date_order'), DATETIME_FORMAT)
		except Exception:
			raise ValidationError(_('Wrong Date Format. Date Should be in format DD/MM/YYYY H:M:S.'))
		if partner_id and salesperson_id and session_id:
			pos_search = pos_obj.search([('partner_id', '=', partner_id.id), ('session_id', '=', session_id.id),
										 ('user_id', '=', salesperson_id.id), ('custom_name', '=', values.get('name'))])
			if pos_search:
				pos_search = pos_search[0]
				pos_id = pos_search
				product_by = self.import_product_by
				line = self.make_pos_line(values, pos_id, product_by)
				currency = pos_id.pricelist_id.currency_id
				pos_id.amount_return = sum(payment.amount < 0 and payment.amount or 0 for payment in pos_id.payment_ids)
				pos_id.amount_tax = currency.round(
					sum(pos_id._amount_line_tax(line, pos_id.fiscal_position_id) for line in pos_id.lines))
				amount_untaxed = currency.round(sum(line.price_subtotal for line in pos_id.lines))
				pos_id.amount_total = pos_id.amount_tax + amount_untaxed
				if pos_id.payment_ids:
					for payment in pos_id.payment_ids:
						payment.amount = pos_id.amount_total
					pos_id.amount_paid = sum(payment.amount for payment in pos_id.payment_ids)
			else:
				pos_id = pos_obj.create({
					'custom_name': values.get('name'),
					'partner_id': partner_id.id or False,
					'user_id': salesperson_id.id or False,
					'session_id': session_id.id or False,
					'date_order': i_date,
					'amount_paid': 0.0,
					'amount_return': 0.0,
					'amount_tax': 0.0,
					'amount_total': 0.0,
					'pos_reference': "Order " + receipt,
				})
				product_by = self.import_product_by
				line = self.make_pos_line(values, pos_id, product_by)

				currency = pos_id.pricelist_id.currency_id
				pos_id.amount_paid = sum(payment.amount for payment in pos_id.payment_ids)
				pos_id.amount_return = sum(payment.amount < 0 and payment.amount or 0 for payment in pos_id.payment_ids)
				pos_id.amount_tax = currency.round(
					sum(pos_id._amount_line_tax(line, pos_id.fiscal_position_id) for line in pos_id.lines))
				amount_untaxed = currency.round(sum(line.price_subtotal for line in pos_id.lines))
				pos_id.amount_total = pos_id.amount_tax + amount_untaxed

				if stage == 'draft' and sequence == 'default_seq':
					pos_id.name = '/'
					pos_id.state = 'draft'
				if stage == 'draft' and sequence == 'custom_seq':
					pos_id.state = 'draft'
					pos_id.name = values.get('name')
				if stage == 'confirm' and sequence == 'default_seq':
					pos_id.add_payment({
						'pos_order_id': pos_id.id,
						'amount': pos_id.amount_total,
						'payment_method_id': self.journal_id.id,
					})
					pos_id.state = 'paid'
					pos_id._create_order_picking()
				if stage == 'confirm' and sequence == 'custom_seq':
					pos_id.name = values.get('name')
					pos_id.add_payment({
						'pos_order_id': pos_id.id,
						'amount': pos_id.amount_total,
						'payment_method_id': self.journal_id.id,
					})
					pos_id.state = 'paid'
					pos_id._create_order_picking()
			return pos_id

	def make_pos_line(self, values, pos_id, product_by):
		pos_line_obj = self.env['pos.order.line']
		pos_obj = self.env['pos.order']

		if values.get('product_id'):
			product_name = values.get('product_id')
			if product_by == 'name':
				if self.check_product(product_name) != None:
					product_id = self.check_product(product_name)
			if product_by == 'code':
				if self.check_product_code(product_name) != None:
					product_id = self.check_product_code(product_name)
			if product_by == 'barcode':
				if self.check_product_barcode(product_name) != None:
					product_id = self.check_product_barcode(product_name)

			if values.get('quantity'):
				quantity = values.get('quantity')
			else:
				quantity = False

			if values.get('price_unit'):
				price_unit = values.get('price_unit')
			else:
				price_unit = False

			if values.get('discount'):
				discount = values.get('discount')
			else:
				discount = False

			tax_ids = []
			if values.get('tax'):
				if ';' in values.get('tax'):
					tax_names = values.get('tax').split(';')
					for name in tax_names:
						tax = self.env['account.tax'].search([('name', '=', name), ('type_tax_use', '=', 'sale')])
						if not tax:
							raise ValidationError(_('"%s" Tax not in your system') % name)
						if len(tax) > 1:
							raise UserError(_('Multiple tax found with the name "%s". Please specify a unique tax name.') % name)
						tax_ids.append(tax.id)

				elif ',' in values.get('tax'):
					tax_names = values.get('tax').split(',')
					for name in tax_names:
						tax = self.env['account.tax'].search([('name', '=', name), ('type_tax_use', '=', 'sale')])

						if not tax:
							raise ValidationError(_('"%s" Tax not in your system') % name)
						if len(tax) > 1:
							raise UserError(_('Multiple tax found with the name "%s". Please specify a unique tax name.') % name)
						tax_ids.append(tax.id)
				else:
					tax_names = values.get('tax').split(',')
					tax = self.env['account.tax'].search([('name', '=', tax_names), ('type_tax_use', '=', 'sale')])
					if not tax:
						raise ValidationError(_('"%s" Tax not in your system') % tax_names)
					if len(tax) > 1:
						raise UserError(_('Multiple tax found with the name "%s". Please specify a unique tax name.') % tax_names)
					tax_ids.append(tax.id)

			line = pos_line_obj.create({
				'full_product_name': product_id.name,
				'product_id': product_id.id,
				'qty': quantity,
				'price_unit': price_unit,
				'discount': discount,
				'order_id': pos_id.id,
				'price_subtotal': 0.0,
				'price_subtotal_incl': 0.0,

			})

			if tax_ids:
				line.write({'tax_ids': ([(6, 0, tax_ids)])})
			line._onchange_amount_line_all()
		return values

	def import_pos_order(self):
		if self.import_option == 'csv':
			if self.file_to_upload:
				file_name = str(self.file_name)
				extension = file_name.split('.')[1]
				if extension not in ['csv','CSV']:
					raise ValidationError(_('Please upload only csv file.!'))

				keys = ['name', 'session', 'date_order', 'salesperson', 'partner_id', 'product_id', 'quantity',
						'price_unit', 'discount', 'tax','receipt']
				csv_data = base64.b64decode(self.file_to_upload)
				data_file = io.StringIO(csv_data.decode("utf-8"))
				data_file.seek(0),
				file_reader = []
				csv_reader = csv.reader(data_file, delimiter=',')
				file_reader.extend(csv_reader)
				values = {}
				lines = []
				sequence = self.sequence_option
				stage = self.order_option
				for i in range(len(file_reader)):
					field = map(str, file_reader[i])
					values = dict(zip(keys, field))
					if values:
						if i == 0:
							continue
						else:
							res = self.make_pos(values, stage,sequence)
			else:
				raise ValidationError(_("Select file!"))
		else:
			if self.file_to_upload:
				file_name = str(self.file_name)
				extension = file_name.split('.')[1]
				if extension not in ['xls','xlsx','XLS','XLSX']:
					raise ValidationError(_('Please upload only xls file.!'))
				fp = tempfile.NamedTemporaryFile(delete=False, suffix=".xlsx")
				fp.write(binascii.a2b_base64(self.file_to_upload))
				fp.seek(0)
				values = {}
				workbook = xlrd.open_workbook(fp.name)
				sheet = workbook.sheet_by_index(0)
				lines = []
				sequence = self.sequence_option
				stage = self.order_option
				for row_no in range(sheet.nrows):
					val = {}
					if row_no <= 0:
						fields = map(lambda row: row.value.encode('utf-8'), sheet.row(row_no))
					else:
						line = list(
							map(lambda row: isinstance(row.value, bytes) and row.value.encode('utf-8') or str(row.value),
								sheet.row(row_no)))
						if len(line) == 11:
							values = {
								'name': line[0],
								'session': line[1],
								'date_order': line[2],
								'salesperson': line[3],
								'partner_id': line[4],
								'product_id': line[5],
								'quantity': line[6],
								'price_unit': line[7],
								'discount': line[8],
								'tax': line[9],
								'receipt': line[10]
							}
							res = self.make_pos(values, stage,sequence)
						else:
							raise ValidationError(_("Wrong File Data Format!"))
			else:
				raise ValidationError(_("Select file!"))