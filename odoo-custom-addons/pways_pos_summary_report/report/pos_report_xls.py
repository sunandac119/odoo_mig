from odoo import models
from datetime import datetime


class ProductXlsx(models.AbstractModel):
    _name = 'report.pways_pos_summary_report.pos_xlsx'
    _inherit = 'report.report_xlsx.abstract'

    def _get_pos_data(self, start_at, stop_at, shop_ids):
        data = []
        domain = [('start_at', '>=', start_at + ' 00:00:00'), ('stop_at', '<=', stop_at + ' 23:59:59')]
        if len(shop_ids):
            domain.append(('config_id', 'in', shop_ids))
        sessions = self.env['pos.session'].search(domain)
        print(">>>>>>>>>>>>>>>>> sessions", sessions)

        bank_method_ids = self.env['pos.payment.method'].search([('is_cash_count', '=', False)])
        cash_method_ids = self.env['pos.payment.method'].search([('is_cash_count', '=', True)])
        for session in sessions:
            bank_payments = session.order_ids.mapped('payment_ids').filtered(
                lambda x: x.payment_method_id.name == 'Bank')
            cash_payments = session.order_ids.mapped('payment_ids').filtered(
                lambda x: x.payment_method_id.name == 'Cash')
            ccard_payments = session.order_ids.mapped('payment_ids').filtered(
                lambda x: x.payment_method_id.name == 'Credit Card')
            dcard_payments = session.order_ids.mapped('payment_ids').filtered(
                lambda x: x.payment_method_id.name == 'Debit Card')
            ewallet_payments = session.order_ids.mapped('payment_ids').filtered(
                lambda x: x.payment_method_id.name == 'E-Wallet')
            ibg_payments = session.order_ids.mapped('payment_ids').filtered(
                lambda x: x.payment_method_id.name == 'IBG')
            credit_payments = session.order_ids.mapped('payment_ids').filtered(
                lambda x: x.payment_method_id.name == 'Credit')

            opening_cash = session.cash_register_balance_start
            cash_sale = sum(cash_payments.mapped('amount'))
            bank_sale = sum(bank_payments.mapped('amount'))
            ccard_sale = sum(ccard_payments.mapped('amount'))
            dcard_sale = sum(dcard_payments.mapped('amount'))
            ewallet_sale = sum(ewallet_payments.mapped('amount'))
            ibg_sale = sum(ibg_payments.mapped('amount'))
            credit_sale = sum(credit_payments.mapped('amount'))

            available_cash = opening_cash + cash_sale
            closing_cash = opening_cash + cash_sale
            data.append({
                'name': session.config_id and session.config_id.name,
                'session': session.name,
                'start_at': session.start_at.strftime("%Y-%m-%d %H:%M:%S"),
                'stop_at': session.stop_at.strftime("%Y-%m-%d %H:%M:%S"),
                'opening_cash': opening_cash,
                'cash_sale': cash_sale,
                'bank_sale': bank_sale,
                'ccard_sale': ccard_sale,
                'dcard_sale': dcard_sale,
                'ewallet_sale': ewallet_sale,
                'ibg_sale': ibg_sale,
                'credit_sale': credit_sale,
                'total_sale': cash_sale + ccard_sale + dcard_sale + ewallet_sale + ibg_sale + credit_sale,
                'available_cash': available_cash,
                'closing_cash': closing_cash,
            })
        print(">>>>>>>>>>> data >>>>>>>>>", data)
        return data

    def _get_pos_total(self, data):
        total_dict = {'opening_cash': 0, 'cash_sale': 0, 'bank_sale': 0, 'ccard_sale': 0, 'dcard_sale': 0,
                      'ewallet_sale': 0, 'ibg_sale': 0, 'credit_sale': 0, 'total_sale': 0, 'available_cash': 0,
                      'closing_cash': 0}
        for val in data:
            total_dict['opening_cash'] += val['opening_cash']
            total_dict['cash_sale'] += val['cash_sale']
            total_dict['bank_sale'] += val['bank_sale']
            total_dict['ccard_sale'] += val['ccard_sale']
            total_dict['dcard_sale'] += val['dcard_sale']
            total_dict['ewallet_sale'] += val['ewallet_sale']
            total_dict['ibg_sale'] += val['ibg_sale']
            total_dict['credit_sale'] += val['credit_sale']
            total_dict['total_sale'] += val['total_sale']
            total_dict['available_cash'] += val['available_cash']
            total_dict['closing_cash'] += val['closing_cash']
        print(">>>>>>>>>>>>>>>>>>>total_dict", total_dict)
        return total_dict

    def generate_xlsx_report(self, workbook, data, products):
        start_at = data.get('start_at')
        stop_at = data.get('stop_at')
        shop_ids = data.get('shop_ids')
        data = self._get_pos_data(start_at, stop_at, shop_ids)

        sheet = workbook.add_worksheet("Retail Summary Report")
        format1 = workbook.add_format({'font_size': 15})
        format2 = workbook.add_format({'font_size': 10, 'bold': True, 'bg_color': '#D3D3D3'})
        format3 = workbook.add_format({'font_size': 10})
        format4 = workbook.add_format({'font_size': 10, 'top': 1, 'bottom': 6})
        format1.set_align('center')

        sheet.merge_range('A1:J2', 'POS Summary Report', format1)
        headers = ["Shop", "Session #", "Opening Date", "Closing Date", 'Opening Cash', 'Cash Sale', 'Bank Sale',
                   'Credit Card Sale', 'Debit Card Sale', 'E-Wallet Sale', 'IBG Sale', 'Credit Sale', 'Total Sale',
                   'Available Cash', 'Closing Cash']
        row = 2
        col = 0
        for header in headers:
            sheet.set_column(col, 1, 18)
            sheet.write(row, col, header, format2)
            col += 1

        row = 3
        col = 0
        for val in data:
            sheet.write(row, col + 0, val['name'], format3)
            sheet.write(row, col + 1, val['session'], format3)
            sheet.write(row, col + 2, val['start_at'], format3)
            sheet.write(row, col + 3, val['stop_at'], format3)
            sheet.write(row, col + 4, val['opening_cash'], format3)
            sheet.write(row, col + 5, val['cash_sale'], format3)
            sheet.write(row, col + 6, val['bank_sale'], format3)
            sheet.write(row, col + 7, val['ccard_sale'], format3)
            sheet.write(row, col + 8, val['dcard_sale'], format3)
            sheet.write(row, col + 9, val['ewallet_sale'], format3)
            sheet.write(row, col + 10, val['ibg_sale'], format3)
            sheet.write(row, col + 11, val['credit_sale'], format3)
            sheet.write(row, col + 12, val['total_sale'], format3)
            sheet.write(row, col + 13, val['available_cash'], format3)
            sheet.write(row, col + 14, val['closing_cash'], format3)
            row += 1

        # Sheet Total
        total_dict = self._get_pos_total(data)
        row += 1
        sheet.write(row, col + 1, 'Total', format1)
        sheet.write(row, col + 4, total_dict['opening_cash'], format4)
        sheet.write(row, col + 5, total_dict['cash_sale'], format4)
        sheet.write(row, col + 6, total_dict['bank_sale'], format4)
        sheet.write(row, col + 7, total_dict['ccard_sale'], format4)
        sheet.write(row, col + 8, total_dict['dcard_sale'], format4)
        sheet.write(row, col + 9, total_dict['ewallet_sale'], format4)
        sheet.write(row, col + 10, total_dict['ibg_sale'], format4)
        sheet.write(row, col + 11, total_dict['credit_sale'], format4)
        sheet.write(row, col + 12, total_dict['total_sale'], format4)
        sheet.write(row, col + 13, total_dict['available_cash'], format4)
        sheet.write(row, col + 14, total_dict['closing_cash'], format4)


    def generate_pdf_report(self, docids, data=None):
        report_data = self._get_report_data(data)  # Implement this method to get report data
        report_name = 'pways_pos_summary_report.pos_xlsx'
        return self.env.ref(report_name).render_qweb_pdf(docids, data=report_data)