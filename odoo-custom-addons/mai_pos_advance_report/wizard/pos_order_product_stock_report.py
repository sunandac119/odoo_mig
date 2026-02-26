import time
from datetime import datetime, timedelta
from dateutil.relativedelta import relativedelta
from odoo.tools.translate import _
from odoo.exceptions import except_orm
from odoo import models, fields, api
from odoo.tools.misc import str2bool, xlwt
from xlwt import easyxf
import pytz
try:
    from odoo.tools.misc import xlsxwriter
except ImportError:
    import xlsxwriter

try:
    from StringIO import StringIO 
except ImportError:
    from io import StringIO,BytesIO  


class POSProductStock(models.TransientModel):
    _name = 'pos.order.product.stock.wizard'
    _description = 'POS Product Stock Report'

    start_date = fields.Datetime(required=True, default=fields.Datetime.now)
    end_date = fields.Datetime(required=True, default=fields.Datetime.now)
    # pos_config_id = fields.Many2one('pos.config', 'Point Of Sale')
    # pos_categ_ids = fields.Many2many('pos.category', string='POS Category')
    product_id = fields.Many2one('product.product', 'Product')
    
    @api.model
    def get_lines(self):
        domain = [
            ('create_date', '>=', self.start_date),
            ('create_date', '<=', self.end_date)
        ]
        if self.product_id:
            domain += [('product_id', '=', self.product_id.id)]

        order_lines = self.env['stock.valuation.layer'].search(domain, order='create_date')
        category_list_data = []
        category_data_dict = {}
        category_data_dict_p = {}
        pre_pre_stock = 0.0
        for line in order_lines:

            # GET USER LOCAL TIME
            tz = pytz.timezone('GMT')
            if self.env.user.tz:
                tz = pytz.timezone(self.env.user.tz)
            tzoffset = tz.utcoffset(line.create_date)
            new_date = line.create_date + tzoffset

            life_date = fields.Datetime.from_string(new_date.date())
            exp = life_date.strftime('%y%m%d')
            
            uniqu_id = int(exp) * line.product_id.id
            if line.product_id.id not in category_data_dict_p:
                category_data_dict_p[line.product_id.id] = {'pre_pre_stock': 0.0}

            domain = [
                ('create_date', '<=', line.create_date),
                ('product_id', '=', line.product_id.id)
            ]
            pre_order_lines = self.env['stock.valuation.layer'].search(domain, order='create_date')
            pre_qty = sum([pol.quantity for pol in pre_order_lines])

            pre_pre_stock = category_data_dict_p[line.product_id.id].get('pre_pre_stock')
            if not pre_pre_stock and pre_qty > 0 and pre_qty == line.quantity:
                quantity = 0.0
            else:
                quantity = line.quantity #abs(line.quantity) if line.quantity < 0 else line.quantity #pre_pre_stock - pre_qty

            if not pre_pre_stock and pre_qty < 0:
                pre_pre_stock = 0.0
            elif not pre_pre_stock:
                pre_pre_stock = pre_qty

            before_stock_amount = line.product_id.standard_price * pre_pre_stock
            sold_stock_amount = quantity * line.product_id.standard_price
            closing_stock_amount = before_stock_amount - sold_stock_amount
            if uniqu_id not in category_list_data:
                suppliers = [l.name.name for l in line.product_id.variant_seller_ids]
                name = line.product_id.pos_categ_id.name
                if pre_qty > 0 and line.quantity and pre_qty == line.quantity:
                    before_stock = pre_qty
                else:
                    before_stock = pre_qty - line.quantity
                if not name:
                    name = "Undefined"
                category_data_dict[uniqu_id] = {
                    'date': new_date.date().strftime('%d/%m/%Y'),
                    'name': name,
                    'suppliers': ", ".join(suppliers),
                    'product_name': line.product_id.display_name,
                    # 'brand_name': line.product_id.product_brand_id.name or "",
                    'before_stock': before_stock,
                    'sold_qty': quantity,
                    'close_stock': pre_pre_stock,
                    'before_stock_amount': 00 if pre_pre_stock == -1 else before_stock_amount,
                    'sold_stock_amount': sold_stock_amount,
                    'closing_stock_amount': closing_stock_amount,
                    'cost_price': line.product_id.standard_price,
                    'pre_pre_stock': pre_qty or 0.0,
                }
                category_data_dict_p[line.product_id.id]['pre_pre_stock'] = pre_qty
                category_list_data.append(uniqu_id)
            else:
                category_data_dict[uniqu_id]['sold_qty'] += quantity
                category_data_dict[uniqu_id]['sold_stock_amount'] += sold_stock_amount
                category_data_dict[uniqu_id]['pre_pre_stock'] = pre_qty
                category_data_dict_p[line.product_id.id]['pre_pre_stock'] = pre_qty

        final_list = []
        for a in category_data_dict:
            final_list.append(category_data_dict.get(a))
        
        final_list = sorted(final_list, key = lambda i: i['date'])
        
        return final_list
    
    def _print_exp_report(self, data):
        res = {}
        import base64
        filename = 'STOCK PRODUCT REPORT.xls'
        workbook = xlwt.Workbook(encoding="UTF-8")
        worksheet = workbook.add_sheet('STOCK PRODUCT REPORT')
        
        header_style = easyxf('font:height 200;pattern: pattern solid, fore_colour gray25; align: horiz center;font: color black; font:bold True;' "borders: top thin,left thin,right thin,bottom thin")
        font_bold = easyxf('font:height 200;pattern: pattern solid, fore_colour gray25; align: horiz center;font: color black; font:bold True;' "borders: top thin,left thin,right thin,bottom thin")


        for i in range(0,11):
            worksheet.col(i).width = 180 * 30
            worksheet.row(i).height = 20 * 15

        worksheet.col(2).width = 180 * 30
        worksheet.col(3).width = 180 * 30


        company_id = self.env.user.company_id

        worksheet.write_merge(0, 1, 0, 10, company_id.name, easyxf(
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


        worksheet.write_merge(7, 7, 0, 9, 'POS Product Stock Report', easyxf(
            'font:height 250; pattern: pattern solid, fore_colour gray25; font: color black; align: horiz center;font:bold True;' "borders: top thin,bottom thin , left thin, right thin"))

        worksheet.write(8, 0, 'DATE', font_bold)
        worksheet.write(8, 1, 'CATEGORY', font_bold)
        worksheet.write(8, 2, 'SUPPLIER', font_bold)
        worksheet.write(8, 3, 'PRODUCT NAME', font_bold)
        # worksheet.write(8, 4, 'BRAND NAME', font_bold)
        worksheet.write(8, 4, 'B/F STOCK', font_bold)
        worksheet.write(8, 5, 'SOLD', font_bold)
        worksheet.write(8, 6, 'CLOSING STOCK', font_bold)
        worksheet.write(8, 7, 'B/F STOCK Amount', font_bold)
        worksheet.write(8, 8, 'SOLD Amount', font_bold)
        worksheet.write(8, 9, 'CLOSING STOCK Amount', font_bold)

        line_details = self.get_lines()
        i = 9
        total_before_stock = 0.0
        total_sold_qty = 0.0
        total_close_stock = 0.0
        total_before_stock_amount = 0.0
        total_sold_stock_amount = 0.0
        total_closing_stock_amount = 0.0
        if line_details:
            style_2 = easyxf('font:height 200; align: horiz right;')
            currency_format = company_id.currency_id.symbol + "#,##0.00"
            style_2.num_format_str = currency_format

            style_3 = easyxf('font:height 200; align: horiz right;')
            style_3.num_format_str = '0.00'
            for line in line_details:
                worksheet.row(i).height = 20 * 25

                total_before_stock += line.get('before_stock')
                total_sold_qty += line.get('sold_qty')
                total_close_stock += line.get('before_stock') + line.get('sold_qty')
                total_before_stock_amount += line.get('before_stock_amount')
                total_sold_stock_amount += line.get('sold_stock_amount')
                total_closing_stock_amount += line.get('before_stock_amount') + line.get('sold_stock_amount')

                worksheet.write(i, 0,line.get('date') ,easyxf('align: horiz center;'))
                worksheet.write(i, 1, line.get('name', '') ,easyxf('align: horiz center;'))
                worksheet.write(i, 2, line.get('suppliers', '') ,easyxf('align: horiz center;'))
                worksheet.write(i, 3, line.get('product_name', '') ,easyxf('align: horiz center;'))
                # worksheet.write(i, 4, line.get('brand_name', '') ,easyxf('align: horiz center;'))
                worksheet.write(i, 4, line.get('before_stock', 0.0), style_3)
                worksheet.write(i, 5, line.get('sold_qty', 0.0), style_3)
                worksheet.write(i, 6, line.get('before_stock') + line.get('sold_qty'), style_3)
                
                worksheet.write(i, 7, line.get('before_stock_amount', 0.0), style_3)
                worksheet.write(i, 8, line.get('sold_stock_amount', 0.0), style_3)
                worksheet.write(i, 9, line.get('before_stock_amount') + line.get('sold_stock_amount'), style_3)
                i += 1

        worksheet.row(i-1).height = 20 * 25
        worksheet.row(i-2).height = 20 * 25
        i += 2
        worksheet.row(i).height = 20 * 25
        foolter_style = easyxf('font:height 200; align: horiz right; font:bold True;')
        currency_format = company_id.currency_id.symbol + "#,##0.00"
        foolter_style.num_format_str = currency_format

        foolter_style_1 = easyxf('font:height 200; align: horiz right; font:bold True;')
        foolter_style_1.num_format_str = '0.00'

        worksheet.write_merge(i, i, 0, 3, 'GRAND TOTAL', font_bold)
        worksheet.write(i, 4, total_before_stock, foolter_style_1)
        worksheet.write(i, 5, total_sold_qty, foolter_style_1)
        worksheet.write(i, 6, total_close_stock, foolter_style_1)
        worksheet.write(i, 7, total_before_stock_amount, foolter_style_1)
        worksheet.write(i, 8, total_sold_stock_amount, foolter_style_1)
        worksheet.write(i, 9, total_closing_stock_amount, foolter_style_1)
            
        import io
        fp = io.BytesIO()
        workbook.save(fp)
        export_id = self.env['pos.product.stock.report'].create(
            {'excel_file': base64.encodestring(fp.getvalue()),
             'file_name': filename},)
        fp.close()
        
        return {
            'view_mode': 'form',
            'res_id': export_id.id,
            'res_model': 'pos.product.stock.report',
            'view_type': 'form',
            'type': 'ir.actions.act_window',
            'context': self._context,
            'target': 'new',
            
        }

    def generate_excel_report(self):
        data = {}
        data['ids'] = self._context.get('active_ids', [])
        data['model'] = self._context.get('active_model', 'ir.ui.menu')
        for record in self:
            data['form'] = record.read(['start_date', 'end_date'])[0]
        return self._print_exp_report(data)

    def generate_pdf_report(self):
        datas = self.get_lines()
        datas = {
             'filter_data': datas,
        }
        return self.env.ref('mai_pos_advance_report.action_print_product_stock_clonet').report_action([], data=datas)

class pos_product_stcok_report_download(models.TransientModel):
    _name = "pos.product.stock.report"
    
    excel_file = fields.Binary('Excel Report')
    file_name = fields.Char('Excel File', size=64)