# -*- coding: utf-8 -*-
import datetime
from datetime import timedelta
import calendar
from odoo import models, fields, api


class AccountCashFlow(models.TransientModel):
    _inherit = "account.common.report"
    _name = "account.cash.flow"
    _description = "Cash Flow"

    no_of_year = fields.Integer(
        string='Previous Period', default=0,
        help="Number of Previous year for which Account Cash-flow"
             "should be printed in the report")
    report_period = fields.Selection(
        selection=[('year_report', 'Yearly Report'),
                   ('date_report', 'Datewise Report')],
        string='Report Period', default='year_report')

    def _print_report(self, data):
        data['form'].update(self.read(
            ['no_of_year', 'company_id', 'report_period'])[0])
        landscape = False
        if self.no_of_year > 2:
            landscape = True
        return self.env.ref(
            'multi_branch_management_axis.action_cash_flow_report').with_context(
            landscape=landscape).report_action(self, data=data)

    def print_pdf_report(self):
        self.ensure_one()
        return self.check_report()

    def print_excel_report(self):
        self.ensure_one()
        return self.env.ref(
            'multi_branch_management_axis.action_cash_flow_excelreport'
        ).report_action(self)

    def get_years(self, is_getdata):
        self.ensure_one()
        company_id = self.company_id
        date_dict = {}
        year_list = [datetime.datetime.now().year - year for year in
                     range(0, self.no_of_year + 1)]
        for year in year_list:
            no_days = calendar.isleap(year) and 365 or 364
            date_dict.update({year: [
                str(datetime.date(year, int(company_id.fiscalyear_last_month),
                                  company_id.fiscalyear_last_day) -
                    timedelta(days=no_days)),
                str(datetime.date(year, int(company_id.fiscalyear_last_month),
                                  company_id.fiscalyear_last_day))]})
        year_list.sort(reverse=True)
        if is_getdata:
            return date_dict
        return year_list

    @api.model
    def get_move_lines(self, target_move, date_from, date_to, key,
                       dummy_list, company_id, report_period):
        move_state = ['draft', 'posted']
        if target_move == 'posted':
            move_state = ['posted']
        query = """SELECT CASE WHEN acc_type.activity_type is null THEN acc.name ELSE acc_type.activity_type END AS activity_type, aml.account_id, aml.date as aml_date, am.state, (aml.debit - aml.credit) * -1 as balance from account_move_line aml, account_account acc, account_move am, account_account_type acc_type where acc.id = aml.account_id and aml.date >= %s and aml.date <= %s and acc.user_type_id = acc_type.id and aml.company_id = %s and am.state in %s group by aml.account_id, acc.name, acc_type.activity_type, am.state, aml.date, aml.debit, aml.credit"""
        params = [date_from, date_to, company_id, tuple(move_state)]
        self._cr.execute(query, params)
        balance_data = self._cr.dictfetchall()
        if report_period == 'year_report':
            [d.update({'year': {key: d['balance']}}) for d in balance_data]
            for dummy in dummy_list:
                [d['year'].update({dummy: 0.0}) for d in balance_data]
        return balance_data

    def get_data(self):
        self.ensure_one()
        final_dict = {}
        balance_data = []
        date_dict = self.get_years(is_getdata=True)
        report_period = self.report_period
        if report_period == 'year_report':
            for key in sorted(date_dict, reverse=True):
                dummy_list = list(date_dict.keys())
                dummy_list.remove(key)
                balance_data += self.get_move_lines(
                    self.target_move or 'all',
                    date_dict[key][0],
                    date_dict[key][1],
                    key,
                    dummy_list, self.company_id.id, report_period)
        else:
            date_from = self.date_from
            date_to = self.date_to
            years = [y for y in range(date_from.year, date_to.year)]
            dummy_list = years
            balance_data += self.get_move_lines(
                self.target_move or 'all', date_from, date_to,
                date_from.year, dummy_list, self.company_id.id,
                report_period)
        for data in balance_data:
            if data['activity_type'] not in final_dict:
                final_dict[data['activity_type']] = {'account': {}}
                if report_period == 'year_report':
                    final_dict[data['activity_type']]['account'] = {
                        data['account_id']: data['year']}
                    final_dict[data['activity_type']]['total'] = data['year']
                else:
                    final_dict[data['activity_type']]['account'] = {
                        data['account_id']: data['balance']}
                    final_dict[data['activity_type']]['total'] = data['balance']
            else:
                if data['account_id'] not in \
                        final_dict[data['activity_type']]['account']:
                    if report_period == 'year_report':
                        final_dict[data['activity_type']
                        ]['account'
                        ][data['account_id']] = data['year']
                    else:
                        final_dict[data['activity_type']
                        ]['account'
                        ][data['account_id']] = data['balance']
                else:
                    f_year = final_dict[
                        data['activity_type']]['account'][data['account_id']]
                    if data.get('year'):
                        d_year = data['year']
                        total = {k: f_year.get(k, 0) + d_year.get(k, 0) for k in
                                 set(f_year.keys()) | set(d_year.keys())}
                        final_dict[data['activity_type']]['account'][data['account_id']] = total
                y_total = final_dict[data['activity_type']]['total']
                if report_period == 'year_report':
                    total = {k: y_total.get(k, 0) + data['year'].get(k, 0) for k in
                             set(y_total.keys()) | set(data['year'].keys())}
                else:
                    total = y_total + final_dict[data['activity_type']]['account'][data['account_id']]
                final_dict[data['activity_type']]['total'] = total
        return final_dict

    @api.model
    def get_acc_details(self, account_id):
        acc_details = {
            'ac_nm': self.env['account.account'].browse(account_id).name,
            'ac_no': self.env['account.account'].browse(account_id).code, }
        return acc_details

    @api.model
    def get_total(self, data_dict, year, type_list):
        total_bal = 0.00
        for value in type_list:
            if value in data_dict:
                if year:
                    total_bal += data_dict[value]['total'][year]
                else:
                    total_bal += data_dict[value]['total']
        return total_bal
