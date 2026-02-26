# -*- coding: utf-8 -*-
# Part of BrowseInfo. See LICENSE file for full copyright and licensing details.

import datetime
import pytz
from odoo import fields, models, api
from odoo.tools.misc import DEFAULT_SERVER_DATETIME_FORMAT
from collections import Counter
import json, ast

MALAYSIA_TZ = pytz.timezone('Asia/Kuala_Lumpur')


class PosConfig(models.Model):
    _inherit = 'pos.config'

    enable_session_report = fields.Boolean(string="Enable Session  Report")


class PosSession(models.Model):
    _inherit = 'pos.session'

    # ==========================================
    #  GMT+8 CONVERSION UTIL
    # ==========================================
    def _to_my_timezone(self, dt):
        """Convert any UTC datetime into Malaysia GMT+8."""
        if not dt:
            return ''
        # ensure datetime object
        if isinstance(dt, str):
            dt = fields.Datetime.from_string(dt)

        dt_utc = dt.replace(tzinfo=pytz.utc)  # stored UTC
        dt_my = dt_utc.astimezone(MALAYSIA_TZ)  # convert to GMT+8
        return dt_my.strftime(DEFAULT_SERVER_DATETIME_FORMAT)

    # ==========================================
    #  SESSION REPORT ACTION
    # ==========================================
    def view_session_report(self):
        return self.env.ref('bi_pos_closed_session_reports.action_report_session_z').report_action(self)

    # ==========================================
    #  CASH OUT
    # ==========================================
    def get_cashout_amount(self):
        cash_out = sum(
            line.amount for statement in self.statement_ids for line in statement.line_ids if line.amount < 0)
        return cash_out

    # ==========================================
    #  CURRENT DATETIME (GMT+8)
    # ==========================================
    def get_current_datetime(self):
        now_utc = datetime.datetime.utcnow().replace(tzinfo=pytz.utc)
        now_my = now_utc.astimezone(MALAYSIA_TZ)
        return now_my.strftime(DEFAULT_SERVER_DATETIME_FORMAT)

    # ==========================================
    #  OPENED DATE (GMT+8)
    # ==========================================
    def get_opened_date(self):
        return self._to_my_timezone(self.start_at)

    # ==========================================
    #  CLOSED DATE (GMT+8)
    # ==========================================
    def get_closed_date(self):
        return self._to_my_timezone(self.stop_at)

    # ==========================================
    #  SESSION AMOUNT DATA
    # ==========================================
    def get_session_amount_data(self):
        pos_order_ids = self.env['pos.order'].search([('session_id', '=', self.id)])
        discount_amount = 0.0
        taxes_amount = 0.0
        total_sale_amount = 0.0
        total_gross_amount = 0.0
        sold_product = {}

        for pos_order in pos_order_ids:
            currency = pos_order.session_id.currency_id
            total_gross_amount += pos_order.amount_total

            for line in pos_order.lines:
                # product count by category
                if line.product_id.pos_categ_id and line.product_id.pos_categ_id.name:
                    if line.product_id.pos_categ_id.name in sold_product:
                        sold_product[line.product_id.pos_categ_id.name] += line.qty
                    else:
                        sold_product.update({line.product_id.pos_categ_id.name: line.qty})
                else:
                    if 'undefine' in sold_product:
                        sold_product['undefine'] += line.qty
                    else:
                        sold_product.update({'undefine': line.qty})

                # taxes
                if line.tax_ids_after_fiscal_position:
                    line_taxes = line.tax_ids_after_fiscal_position.compute_all(
                        line.price_unit * (1 - (line.discount or 0.0) / 100.0),
                        currency, line.qty, product=line.product_id, partner=line.order_id.partner_id or False)
                    for tax in line_taxes['taxes']:
                        taxes_amount += tax.get('amount', 0)

                # discounts
                if line.discount > 0:
                    discount_amount += (((line.price_unit * line.qty) * line.discount) / 100)

                # sale total
                if line.qty > 0:
                    total_sale_amount += line.price_unit * line.qty

        return {
            'total_sale': total_gross_amount,
            'discount': discount_amount,
            'tax': taxes_amount,
            'products_sold': sold_product,
            'total_gross': total_gross_amount - taxes_amount - discount_amount,
            'final_total': (total_gross_amount - discount_amount)
        }

    # ==========================================
    #  TAXES
    # ==========================================
    def get_taxes_data(self):
        order_ids = self.env['pos.order'].search([('session_id', '=', self.id)])
        taxes = {}

        for order in order_ids:
            currency = order.pricelist_id.currency_id

            for line in order.lines:
                if line.tax_ids_after_fiscal_position:

                    for tax in line.tax_ids_after_fiscal_position:
                        discount_amount = 0
                        if line.discount > 0:
                            discount_amount = ((line.qty * line.price_unit) * line.discount) / 100

                        untaxed_amount = (line.qty * line.price_unit) - discount_amount
                        tax_percentage = 0

                        if tax.amount_type == 'group':
                            for child_tax in tax.children_tax_ids:
                                tax_percentage += child_tax.amount
                        else:
                            tax_percentage += tax.amount

                        tax_amount = ((untaxed_amount * tax_percentage) / 100)

                        if tax.name:
                            if tax.name in taxes:
                                taxes[tax.name] += tax_amount
                            else:
                                taxes.update({tax.name: tax_amount})
                        else:
                            if 'undefine' in taxes:
                                taxes['undefine'] += tax_amount
                            else:
                                taxes.update({'undefine': tax_amount})

        return taxes

    # ==========================================
    #  PRICELIST TOTAL
    # ==========================================
    def get_pricelist(self):
        pos_order_ids = self.env['pos.order'].search([('session_id', '=', self.id)])
        pricelist = {}

        for pos_order in pos_order_ids:
            if pos_order.pricelist_id.name:
                if pos_order.pricelist_id.name in pricelist:
                    pricelist[pos_order.pricelist_id.name] += pos_order.amount_total
                else:
                    pricelist.update({pos_order.pricelist_id.name: pos_order.amount_total})
            else:
                if 'undefine' in pricelist:
                    pricelist['undefine'] += pos_order.amount_total
                else:
                    pricelist.update({'undefine': pos_order.amount_total})

        return pricelist

    # ==========================================
    #  PRICELIST QTY
    # ==========================================
    def get_pricelist_qty(self, pricelist):
        if pricelist:
            qty_pricelist = 0
            pricelist_obj = self.env['product.pricelist'].search([('name', '=', str(pricelist))])

            if pricelist_obj:
                pos_order_ids = self.env['pos.order'].search(
                    [('session_id', '=', self.id), ('pricelist_id.id', '=', pricelist_obj.id)])
                qty_pricelist = len(pos_order_ids)

            else:
                if pricelist == 'undefine':
                    pos_order_ids = self.env['pos.order'].search(
                        [('session_id', '=', self.id), ('pricelist_id', '=', False)])
                    qty_pricelist = len(pos_order_ids)

            return int(qty_pricelist)

    # ==========================================
    #  PAYMENT DETAILS
    # ==========================================
    def get_payment_data(self):
        pos_order_ids = self.env['pos.order'].search([('session_id', '=', self.id)])
        st_line_ids = self.env["pos.payment"].search([('pos_order_id', 'in', pos_order_ids.ids)]).ids

        if st_line_ids:
            self.env.cr.execute("""
                SELECT ppm.name, sum(amount) total
                FROM pos_payment AS pp,
                     pos_payment_method AS ppm
                WHERE pp.payment_method_id = ppm.id 
                  AND pp.id IN %s 
                GROUP BY ppm.name
            """, (tuple(st_line_ids),))

            payments = self.env.cr.dictfetchall()
        else:
            payments = []

        return payments

    # ==========================================
    #  PAYMENT QTY
    # ==========================================
    def get_payment_qty(self, payment_method):
        qty_payment_method = 0

        if payment_method:
            orders = self.env['pos.order'].search([('session_id', '=', self.id)])
            st_line_obj = self.env["account.bank.statement.line"].search([('pos_statement_id', 'in', orders.ids)])

            if len(st_line_obj) > 0:
                res = []
                for line in st_line_obj:
                    res.append(line.journal_id.name)
                res_dict = ast.literal_eval(json.dumps(dict(Counter(res))))

                if payment_method in res_dict:
                    qty_payment_method = res_dict[payment_method]

        return int(qty_payment_method)
