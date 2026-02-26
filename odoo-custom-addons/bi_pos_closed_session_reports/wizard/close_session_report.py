# -*- coding: utf-8 -*-
# Part of BrowseInfo. See LICENSE file for full copyright and licensing details.

from datetime import datetime
from odoo import api, fields, models, _
import pytz


class PosCloseSessionReport(models.TransientModel):
    _name = 'close.session.report.wiz'

    pos_session_ids = fields.Many2many(
        'pos.session',
        string="POS Session(s)",
        domain="[('state', 'in', ['closed'])]",
        required=True
    )
    report_type = fields.Char('Report Type', readonly=True, default='PDF')
    company_id = fields.Many2one('res.company', "Company")

    def generate_close_session_report(self):
        data = {
            'session_ids': self.pos_session_ids.ids,
            'company': self.company_id.id
        }
        return self.env.ref(
            'bi_pos_closed_session_reports.action_close_session_report_print'
        ).report_action([], data=data)


class ClosedSessionReport(models.AbstractModel):
    _name = 'report.bi_pos_closed_session_reports.report_closed_session'
    _description = 'Closed Session Point of Sale Details'

    @api.model
    def get_sale_details(self, sessions=False, company=False):
        if sessions:
            orders = self.env['pos.order'].search([
                ('session_id.state', 'in', ['closed']),
                ('session_id', 'in', sessions.ids)
            ])

        user_currency = self.env.user.company_id.currency_id

        total = total_tax = total_discount = return_total = 0.0
        categories_data = {}

        for order in orders:
            amount_total = order.amount_total
            if user_currency != order.pricelist_id.currency_id:
                amount_total = order.pricelist_id.currency_id._convert(
                    amount_total, user_currency, order.company_id, order.date_order or fields.Date.today()
                )
            total += amount_total
            total_tax += order.amount_tax

            for line in order.payment_ids:
                if line.name and 'return' in line.name:
                    return_total += abs(line.amount)

            for line in order.lines:
                total_discount += line.qty * line.price_unit - line.price_subtotal
                category = line.product_id.pos_categ_id.name
                if category in categories_data:
                    categories_data[category]['total'] += line.price_subtotal_incl
                else:
                    categories_data[category] = {
                        'name': category,
                        'total': line.price_subtotal_incl
                    }

        categories_tot = list(categories_data.values())

        st_line_ids = self.env["pos.payment"].search([('pos_order_id', 'in', orders.ids)]).ids
        if st_line_ids:
            self.env.cr.execute("""
                SELECT ppm.name, SUM(amount) AS total
                FROM pos_payment pp
                JOIN pos_payment_method ppm ON pp.payment_method_id = ppm.id
                WHERE pp.id IN %s
                GROUP BY ppm.name
            """, (tuple(st_line_ids),))
            payments = self.env.cr.dictfetchall()
        else:
            payments = []

        # Convert datetime to Kuala Lumpur timezone
        tz = pytz.timezone('Asia/Kuala_Lumpur')
        local_now = datetime.now(tz)

        # ✅ Correct field: cash_real_difference
        opening_balance = sum(s.cash_register_balance_start for s in sessions)
        clsoing_balance = sum(s.cash_register_balance_end_real for s in sessions)
        control_diff = sum(s.cash_real_difference for s in sessions)

        num_sessions = ', '.join(s.name for s in sessions)

        return {
            'currency_precision': 2,
            'total_paid': user_currency.round(total),
            'payments': payments,
            'company_name': self.env.user.company_id.name,
            'taxes': float(total_tax),
            'num_sessions': num_sessions,
            'categories_data': categories_tot,
            'total_discount': total_discount,
            'print_date': local_now,
            'return_total': return_total,
            'opening_balance': opening_balance,
            'clsoing_balance': "{:.2f}".format(clsoing_balance),
            'control_diff': control_diff,
            'company': company,
        }

    def _get_report_values(self, docids, data=None):
        data = dict(data or {})
        sessions = self.env['pos.session'].search([('id', 'in', data['session_ids'])], order='id asc')
        company = self.env['res.company'].browse(data['company'])
        data.update(self.get_sale_details(sessions, company))
        return data
