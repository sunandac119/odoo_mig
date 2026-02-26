# -*- coding: utf-8 -*-
from odoo import models, api
import datetime
from datetime import timedelta
import calendar


class ReportAccountCashFlow(models.TransientModel):
    _name = 'report.multi_branch_management_axis.report_cashflow'
    _description = 'Account Cashflow report model'

    @api.model
    def get_years(self, data, is_getdata):
        company_id = self.env['res.company'].browse(
            data['form']['company_id'][0])
        date_dict = {}
        year_list = [datetime.datetime.now().year - year for year in
                     range(0, data['form']['no_of_year'] + 1)]
        for year in year_list:
            no_days = calendar.isleap(year) and 365 or 364
            arg_month = int(company_id.fiscalyear_last_month)
            arg_day = int(company_id.fiscalyear_last_day)
            date_dict.update({year: [
                str(datetime.date(year, arg_month,
                                  arg_day) -
                    timedelta(days=no_days)),
                str(datetime.date(year, arg_month,
                                  arg_day))]})
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

    @api.model
    def get_data(self, data):
        final_dict = {}
        balance_data = []
        date_dict = self.get_years(data, is_getdata=True)
        report_period = data['form']['report_period']
        if report_period == 'year_report':
            for key in sorted(date_dict, reverse=True):
                dummy_list = list(date_dict.keys())
                dummy_list.remove(key)
                balance_data += self.get_move_lines(
                    data['form'].get('target_move', 'all'),
                    date_dict[key][0],
                    date_dict[key][1],
                    key, dummy_list,
                    data['form']['company_id'][0], report_period)
        else:
            date_from = data['form']['date_from']
            date_to = data['form']['date_to']
            date_from = datetime.datetime.strptime(date_from, '%Y-%m-%d')
            date_to = datetime.datetime.strptime(date_to, '%Y-%m-%d')
            years = [y for y in range(date_from.year, date_to.year)]
            dummy_list = years
            balance_data += self.get_move_lines(
                data['form'].get('target_move', 'all'), date_from, date_to,
                date_from.year, dummy_list, data['form']['company_id'][0],
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
                    if report_period == 'year_report':
                        f_year = final_dict[
                            data['activity_type']]['account'][data['account_id']]
                        d_year = data['year']
                        total = {k: f_year.get(k, 0) + d_year.get(k, 0) for k in set(f_year.keys()) | set(d_year.keys())}
                        final_dict[data['activity_type']]['account'][data['account_id']] = total
                    else:
                        final_dict[data['activity_type']]['account'][data['account_id']] = data['balance']
                y_total = final_dict[data['activity_type']]['total']
                if report_period == 'year_report':
                    total = {k: y_total.get(k, 0) + data['year'].get(k, 0) for k in set(y_total.keys()) | set(data['year'].keys())}
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

    @api.model
    def _get_report_values(self, docids, data=None):
        docs = self.env['account.move.line'].browse(docids)
        if data['form']['report_period'] == 'year_report':
            yearly = True
        else:
            yearly = False
        if yearly:
            get_years = self.get_years(data, is_getdata=False)
        else:
            get_years = []
        docargs = {
            'doc_model': 'account.move.line',
            'docs': docs,
            'get_data': self.get_data(data),
            'yearly': yearly,
            'start_date': data['form']['date_from'],
            'end_date': data['form']['date_to'],
            'get_years': get_years,
            'get_acc_details': self.get_acc_details,
            'get_total': self.get_total,
        }
        return docargs
