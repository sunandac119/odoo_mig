# -*- coding: utf-8 -*-

from odoo import models, fields, api
from datetime import datetime

class AccountBankStmtCashWizardExt(models.Model):
    _inherit = 'account.bank.statement.cashbox'

    @api.model
    def default_get(self, fields_list):
        defaults = super(AccountBankStmtCashWizardExt, self).default_get(fields_list)
        
        amount_list = [0.05, 0.10, 0.20, 0.50, 1.00, 5.00, 10.00, 20.00, 50.00, 100.00]
        cashbox_lines_list = []
        for amount in amount_list:
            cashbox_lines_list.append((0, 0, {
                'coin_value': amount,
            }))
        defaults.update({
            'cashbox_lines_ids': cashbox_lines_list,
        })
        return defaults

    def generate_cash_out_report(self):
        # Get the current active pos_session array
        uid = self.env.uid
        pos_session = self.env['pos.session'].search([('state', '=', 'opened'), ('user_id', '=', uid)], limit=1)
        active_ids = [pos_session.id]

        cash_box_list = []
        subtotal = 0.0
        value_total = 0.0
        qty_total = 0.0
        for rec in self.cashbox_lines_ids:
            cash_dict = {
                'value': round(rec.coin_value, 2),
                'code': round(rec.number, 2),
                'subtotal': round(rec.subtotal, 2)
            }
            subtotal += rec.subtotal
            value_total += rec.coin_value
            qty_total += rec.number
            cash_box_list.append(cash_dict)

        # Additional session information
        counter_names = pos_session.mapped('config_id')
        cashier_names = pos_session.mapped('user_id.name')
        
        # Ensure the 'start_at' field is a valid string before conversion
        formatted_session_times = pos_session.mapped(lambda session: datetime.strptime(session.start_at, "%d-%m-%Y %H:%M").strftime("%d-%m-%Y %H:%M") if isinstance(session.start_at, str) else '')

        data = {
            'report_name': "CLOSE BALENCE",
            'session_ids': active_ids,
            'cash_box_list': cash_box_list,
            'value_total': value_total,
            'qty_total': qty_total,
            'total': subtotal,
			'session': active_ids,
            'counter_name': ', '.join(counter_names),
            'cashier_name': ', '.join(cashier_names),
            'formatted_session_time': ', '.join(formatted_session_times),
        }
        return self.env.ref('pos_extend.action_cash_box_out_close_report_print').report_action([], data=data)

    def generate_cash_out_report_1(self):
        context = dict(self._context or {})
        active_model = context.get('active_model', False)

        # Get the current active pos_session array
        pos_sessions = self.env['pos.session'].search([('state', '=', 'opened')])
        active_ids = pos_sessions.ids

        cash_box_list = []
        subtotal = 0.0
        value_total = 0.0
        qty_total = 0.0
        for rec in self.cashbox_lines_ids:
            cash_dict = {
                'value': round(rec.coin_value, 2),
                'code': round(rec.number, 2),
                'subtotal': round(rec.subtotal, 2)
            }
            subtotal += rec.subtotal
            value_total += rec.coin_value
            qty_total += rec.number
            cash_box_list.append(cash_dict)

        # Additional session information
        counter_names = pos_sessions.mapped('config_id.name')
        cashier_names = pos_sessions.mapped('user_id.name')

        # Ensure the 'start_at' field is a valid string before conversion
        formatted_session_times = pos_sessions.mapped(lambda session: datetime.strptime(session.start_at, "%Y-%m-%d %H:%M:%S").strftime("%Y-%m-%d %H:%M:%S") if isinstance(session.start_at, str) else '')

        data = {
            'report_name': "CLOSE BALANCE",
            'session_ids': active_ids,
            'cash_box_list': cash_box_list,
            'value_total': value_total,
            'qty_total': qty_total,
            'total': subtotal,
            'counter_name': ', '.join(counter_names),
            'cashier_name': ', '.join(cashier_names),
            'formatted_session_time': ', '.join(formatted_session_times),
        }
        return self.env.ref('pos_extend.action_cash_box_out_close_report_1_print').report_action([], data=data)


class PosExtend(models.TransientModel):
    _inherit = 'cash.box.out'
    _description = 'Cash Box Out'

    def _get_company_currency(self):
        for partner in self:
            partner.currency_id = self.env.company.currency_id

    cashbox_lines_ids = fields.One2many('cash.box.out.line', 'cashbox_id', string='Cashbox Lines')
    total = fields.Float(compute='_compute_total')
    currency_id = fields.Many2one('res.currency', compute='_get_company_currency', readonly=True,
                                  string="Currency", help='Utility field to express amount currency')

    @api.model
    def default_get(self, fields_list):
        defaults = super(PosExtend, self).default_get(fields_list)
        
        amount_list = [0.05, 0.10, 0.20, 0.50, 1.00, 5.00, 10.00, 20.00, 50.00, 100.00]
        cashbox_lines_list = []
        for amount in amount_list:
            cashbox_lines_list.append((0, 0, {
                'coin_value': amount,
            }))
        name = self.env['ir.sequence'].next_by_code('cash.box.out')
        defaults.update({
            'cashbox_lines_ids': cashbox_lines_list,
            'name': name
        })
        return defaults
    
    @api.depends('cashbox_lines_ids', 'cashbox_lines_ids.coin_value', 'cashbox_lines_ids.number')
    def _compute_total(self):
        for cashbox in self:
            cashbox.total = sum([line.subtotal for line in cashbox.cashbox_lines_ids])

    def cash_in_action(self):
        self.ensure_one()
        self.write({
            'amount': self.total
        })
        view_id = self.env.ref('account.cash_box_out_form').id
        return {
            'context': self.env.context,
            'view_type': 'form',
            'view_mode': 'form',
            'res_model': 'cash.box.out',
            'res_id': self.id,
            'view_id': view_id,
            'type': 'ir.actions.act_window',
            'target': 'new',
        }

    def cash_out_action(self):
        self.ensure_one()
        self.write({
            'amount': -self.total
        })
        view_id = self.env.ref('account.cash_box_out_form').id
        return {
            'context': self.env.context,
            'view_type': 'form',
            'view_mode': 'form',
            'res_model': 'cash.box.out',
            'res_id': self.id,
            'view_id': view_id,
            'type': 'ir.actions.act_window',
            'target': 'new',
        }


class CashBoxOutLine(models.TransientModel):
    _name = 'cash.box.out.line'

    @api.depends('coin_value', 'number')
    def _sub_total(self):
        """Calculates Subtotal"""
        for cashbox_line in self:
            cashbox_line.subtotal = cashbox_line.coin_value * cashbox_line.number

    coin_value = fields.Float(string='Coin/Bill Value', required=True, digits=0)
    number = fields.Integer(string='#Coins/Bills', help='Opening Unit Numbers')
    subtotal = fields.Float(compute='_sub_total', string='Subtotal', digits=0, readonly=True)
    cashbox_id = fields.Many2one('cash.box.out', string="Cashbox")
    currency_id = fields.Many2one('res.currency', related='cashbox_id.currency_id')
