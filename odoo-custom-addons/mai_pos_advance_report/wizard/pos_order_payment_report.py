import time
from datetime import datetime
from dateutil.relativedelta import relativedelta
from odoo.tools.translate import _
from odoo.exceptions import except_orm
from odoo import models, fields, api
from odoo.tools.misc import str2bool, xlwt
from xlwt import easyxf

try:
    from odoo.tools.misc import xlsxwriter
except ImportError:
    import xlsxwriter

try:
    from StringIO import StringIO 
except ImportError:
    from io import StringIO,BytesIO  


class PosDetailsExcel(models.TransientModel):
    _name = 'pos.order.payment.wizard'
    _description = 'POS order Payment Report'

    start_date = fields.Datetime(required=True)
    end_date = fields.Datetime(required=True, default=fields.Datetime.now)
    pos_ids = fields.Many2many('pos.config',string='Point Of Sale')
    
    @api.model
    def get_lines(self):
        vals = []
        
        domain = [
            ('state', 'in', ['paid','done','invoiced']),
            ('date_order', '>=', self.start_date),
            ('date_order', '<=', self.end_date)
        ]
        if self.pos_ids:
            domain += [('config_id','in', self.pos_ids.ids)]
        order = self.env['pos.order'].search(domain)
        for pos in order:
            return_check = False
            if pos.amount_total < 0:
                return_check = True

            vals.append({
                'pos_name': pos.config_id.name,
                'name': pos.name,
                'session_name': pos.session_id.name,
                'date_order': pos.date_order,
                'receipt_ref':pos.pos_reference,
                'return': pos.name if return_check else '',
                'partner_id': pos.partner_id.name or '',
                'sales_person': pos.user_id.name or '',
                'order_id': pos.id,
                'length': len(pos.ids),
                'total': pos.amount_total,
            })

        return vals
    
    def _print_exp_report(self, data):
        res = {}
        import base64
        filename = 'POS Payment Collection Report.xls'
        workbook = xlwt.Workbook(encoding="UTF-8")
        worksheet = workbook.add_sheet('POS Payment Collection Report')
        
        header_style = easyxf('font:height 200;pattern: pattern solid, fore_colour gray25; align: horiz center;font: color black; font:bold True;' "borders: top thin,left thin,right thin,bottom thin")
        font_bold = easyxf('font:height 200;pattern: pattern solid, fore_colour gray25; align: horiz left;font: color black; font:bold True;' "borders: top thin,left thin,right thin,bottom thin")

        pay_ids = self.env['pos.payment.method'].search([])
        raw_length = 7 + len(pay_ids)
        worksheet.write_merge(8, 8, 8, raw_length, 'Payment Method ', header_style)
        col_count = 8
        pay_data_dict = {}
        for pay in pay_ids:
            worksheet.write(9, col_count, pay.name, header_style)
            pay_data_dict[col_count] = pay.id 
            col_count += 1

        worksheet.col(0).width = 180 * 30
        worksheet.col(1).width = 180 * 30
        worksheet.col(2).width = 180 * 30
        worksheet.col(3).width = 180 * 30
        worksheet.col(4).width = 180 * 30
        worksheet.col(5).width = 180 * 30
        for index in range(6, 20):
            if index in [12, 16]:
                worksheet.col(index).width = 210 * 30
            else:
                worksheet.col(index).width = 180 * 30
        company_id = self.env.user.company_id
        worksheet.write_merge(0, 1, 0, col_count, company_id.name, easyxf(
            'font:height 400; align: horiz center;font:bold True;' "borders: top thin,bottom thin , left thin, right thin"))
        worksheet.write(3, 1, 'Start Date', font_bold)

        date_from = data['form']['start_date']
        date_end = data['form']['end_date']
        address = ''
        if company_id.street:
            address += company_id.street
        if company_id.street2:
            address +=  ', ' + company_id.street2
        if company_id.city:
            address +=  ', ' + company_id.city
        if company_id.state_id:
            address +=  ', ' + company_id.state_id.name
        if company_id.zip:
            address +=  '-' + company_id.zip
        if company_id.country_id:
            address +=  ', ' + company_id.country_id.name

        worksheet.write_merge(3, 3, 2, 3, str(date_from))
        worksheet.write(4, 1, 'End Date', font_bold)
        worksheet.write_merge(4, 4, 2, 3, str(date_end))
        worksheet.write(5, 1, 'Address', font_bold)
        worksheet.write_merge(5, 5, 2, 6, address)
        
        worksheet.write_merge(7, 7, 0, col_count, 'POS Payment Collection Report', header_style)        

        worksheet.write_merge(8, 9, 0, 0, 'Point Of Sale', header_style)
        worksheet.write_merge(8, 9, 1, 1, 'Order Ref', header_style)
        worksheet.write_merge(8, 9, 2, 2, 'Session', header_style)
        worksheet.write_merge(8, 9, 3, 3, 'Date ', header_style)

        worksheet.write_merge(8, 9, 4, 4, 'Receipt Number', header_style)
        worksheet.write_merge(8, 9, 5, 5, 'Return Order', header_style)
        worksheet.write_merge(8, 9, 6, 6, 'Customer', header_style)
        worksheet.write_merge(8, 9, 7, 7, 'Sales Person  ', header_style)

        worksheet.write_merge(8, 9, col_count, col_count, 'Total', header_style)
        line_details = self.get_lines()
        if line_details:
            i = 10
            total_total = 0
            style_2 = easyxf('font:height 200; align: horiz right;')
            style_2.num_format_str = '0.00'
            check_lenght = 0
            pay_length = 8
            total_payment_dict = {}
            for line in line_details:
                total_total += line.get('total')
                worksheet.row(i).height = 20 * 15
                worksheet.write(i, 0, line.get('pos_name', False))
                worksheet.write(i, 1, line.get('name', False))
                worksheet.write(i, 2, line.get('session_name', False))
                worksheet.write(i, 3, line.get('date_order').strftime("%Y-%m-%d, %H:%M:%S"))
                worksheet.write(i, 4, line.get('receipt_ref'))
                worksheet.write(i, 5, line.get('return'))
                worksheet.write(i, 6, line.get('partner_id'))
                worksheet.write(i, 7, line.get('sales_person', False))

                check_lenght += 1
                if check_lenght == line.get('length'):
                    a = i - int(line.get('length'))
                    for p in pay_ids:
                        value =  pay_data_dict.get(pay_length)
                        final_amount = 0.0
                        if value == p.id:
                            absl_ids = self.env['pos.payment'].search([('pos_order_id', '=', line.get('order_id')), ('payment_method_id', '=', p.id)])
                            final_amount = sum([absl_id.amount for absl_id in absl_ids])
                        if value not in total_payment_dict:
                            total_payment_dict[value] = final_amount
                        else:
                            total_payment_dict[value] += final_amount
                        worksheet.write_merge(a + 1, i, pay_length, pay_length, final_amount, style_2)
                        pay_length += 1

                    check_lenght = 0
                    pay_length = 8
                worksheet.write(i, col_count, line.get('total', False))
                i += 1

            foolter_style = easyxf('font:height 200; align: horiz right; font:bold True;')
            foolter_style.num_format_str = '0.00'
            worksheet.write(i, 7, 'TOTAL', header_style)

            pay_length = 8
            all_payment_total = 0.0
            for p in pay_ids:
                worksheet.write(i, pay_length, total_payment_dict.get(p.id), foolter_style)
                all_payment_total += total_payment_dict.get(p.id)
                pay_length += 1

            worksheet.write(i, pay_length, total_total, foolter_style)
            i += 3

            Summary_style = easyxf('font:height 200;pattern: pattern solid, fore_colour gray25;font: color black; font:bold True;' "borders: top thin,left thin,right thin,bottom thin")
            worksheet.row(i).height = 20 * 15
            worksheet.write_merge(i, i, 1, 2, 'PAYMENT DETAILS', Summary_style)
            i += 1
            worksheet.row(i).height = 20 * 15
            worksheet.write(i, 1, 'Payment Method', Summary_style)
            worksheet.write(i, 2, 'Amount', Summary_style)

            i += 1
            for p in pay_ids:
                payment_id = self.env['pos.payment.method'].browse(p.id)
                worksheet.write(i, 1, payment_id.name)
                worksheet.write(i, 2, total_payment_dict.get(p.id), foolter_style)
                i+=1

            i+=1
            worksheet.write(i, 1, 'Total', Summary_style)
            worksheet.write(i, 2, all_payment_total, foolter_style)

        import io
        fp = io.BytesIO()
        workbook.save(fp)
        export_id = self.env['pos.payment.report.download'].create(
            {'excel_file': base64.encodestring(fp.getvalue()),
             'file_name': filename},)
        fp.close()
        
        return {
            'view_mode': 'form',
            'res_id': export_id.id,
            'res_model': 'pos.payment.report.download',
            'view_type': 'form',
            'type': 'ir.actions.act_window',
            'context': self._context,
            'target': 'new',
            
        }

    def generate_report(self):
        data = {}
        data['ids'] = self._context.get('active_ids', [])
        data['model'] = self._context.get('active_model', 'ir.ui.menu')
        for record in self:
            data['form'] = record.read(['start_date', 'end_date'])[0]
        return self._print_exp_report(data)


    def generate_pdf_report(self):
        datas = self.get_lines()
        pay_ids = self.env['pos.payment.method'].search([])
        payment_method_list = []
        payment_method_ids = []
        for pay in pay_ids:
            payment_method_list.append(pay.name)
            payment_method_ids.append(pay.id)

        datas = {
             'filter_data': datas,
             'payment_method_list': payment_method_list,
             'payment_method_ids': payment_method_ids,
        }
        return self.env.ref('mai_pos_advance_report.action_print_payment_clonet').report_action([], data=datas)

class pos_excel_report_download(models.TransientModel):
    _name = "pos.payment.report.download"
    
    excel_file = fields.Binary('Excel Report')
    file_name = fields.Char('Excel File', size=64)