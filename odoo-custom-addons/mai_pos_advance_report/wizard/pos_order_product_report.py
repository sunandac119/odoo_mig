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


class POSProduct(models.TransientModel):
    _name = 'pos.order.product.wizard'
    _description = 'POS Product Report'

    start_date = fields.Datetime(required=True, default=fields.Datetime.now)
    end_date = fields.Datetime(required=True, default=fields.Datetime.now)
    pos_config_id = fields.Many2one('pos.config', 'Point Of Sale')
    pos_categ_ids = fields.Many2many('pos.category', string='POS Category')
    product_id = fields.Many2one('product.product', 'Product')
    
    @api.model
    def get_lines(self):
        domain = [
            ('order_id.state', 'in', ['paid','done','invoiced']),
            ('order_id.date_order', '>=', self.start_date),
            ('order_id.date_order', '<=', self.end_date)
        ]

        if self.pos_config_id:
            domain += [('order_id.config_id','=', self.pos_config_id.id)]
        # else:
        #     pos_ids = self.pos_config_id.search([])
        #     domain += [('order_id.config_id','in', pos_ids.ids)]

        POS_categ_obj = self.env['pos.category']
        if self.pos_categ_ids:
            domain += [('product_id.pos_categ_id', 'child_of', self.pos_categ_ids.ids)]
        # else:
        #     pos_categ_ids = self.env['pos.category'].search([])
        #     domain += [('product_id.pos_categ_id', 'child_of', pos_categ_ids.ids)]

        if self.product_id:
            domain += [('product_id', '=', self.product_id.id)]

        order_lines = self.env['pos.order.line'].search(domain)
        category_list_data = []
        category_data_dict = {}
        for line in order_lines:
            life_date = fields.Datetime.from_string(line.order_id.date_order.date())
            exp = life_date.strftime('%y%m%d')
            # uniqu_id = int(exp) + line.product_id.pos_categ_id.id + line.product_id.id
            uniqu_id = int(exp) * line.product_id.id
            gross_profit = line.price_subtotal_incl - line.product_id.standard_price
            tax_amount = line.price_subtotal_incl - line.price_subtotal
            total_cost = line.qty * line.product_id.standard_price
            gross_profit = line.price_subtotal - total_cost
            if uniqu_id not in category_list_data:
                suppliers = [l.name.name for l in line.product_id.variant_seller_ids]

                name = line.product_id.pos_categ_id.name
                if not name:
                    name = "Undefined"
                category_data_dict[uniqu_id] = {
                    'name': name,
                    'suppliers': ", ".join(suppliers),
                    'product_name': line.product_id.display_name,
                    # 'brand_name': line.product_id.product_brand_id.name or "",
                    'qty': line.qty,
                    'sale_amount': line.price_subtotal,
                    'tax_amount': tax_amount,
                    'cost': line.product_id.standard_price,
                    'sale': line.product_id.lst_price,
                    'total_cost': total_cost,
                    'gross_profit': gross_profit,
                    'date': line.order_id.date_order.date().strftime('%d/%m/%Y'),
                }
                category_list_data.append(uniqu_id)
            else:
                category_data_dict[uniqu_id]['qty'] += line.qty
                category_data_dict[uniqu_id]['sale_amount'] += line.price_subtotal_incl
                category_data_dict[uniqu_id]['tax_amount'] += tax_amount
                # category_data_dict[uniqu_id]['cost'] += line.product_id.standard_price
                category_data_dict[uniqu_id]['total_cost'] += total_cost
                category_data_dict[uniqu_id]['gross_profit'] += gross_profit

        final_list = []
        for a in category_data_dict:
            final_list.append(category_data_dict.get(a))
        
        final_list = sorted(final_list, key = lambda i: i['date'])
        return final_list
    
    def _print_exp_report(self, data):
        res = {}
        import base64
        filename = 'POS Product wise Sales Report.xls'
        workbook = xlwt.Workbook(encoding="UTF-8")
        worksheet = workbook.add_sheet('POS Product wise Sales Report”')
        
        header_style = easyxf('font:height 200;pattern: pattern solid, fore_colour gray25; align: horiz center;font: color black; font:bold True;' "borders: top thin,left thin,right thin,bottom thin")
        font_bold = easyxf('font:height 200;pattern: pattern solid, fore_colour gray25; align: horiz center;font: color black; font:bold True;' "borders: top thin,left thin,right thin,bottom thin")

        for i in range(0,10):
            worksheet.col(i).width = 130 * 30
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

        worksheet.write_merge(7, 7, 0, 11, 'POS Product Wise Sales Report', easyxf(
            'font:height 250; pattern: pattern solid, fore_colour gray25; font: color black; align: horiz center;font:bold True;' "borders: top thin,bottom thin , left thin, right thin"))

        worksheet.write(8, 0, 'DATE', font_bold)
        worksheet.write(8, 1, 'CATEGORY', font_bold)
        worksheet.write(8, 2, 'SUPPLIER', font_bold)
        worksheet.write(8, 3, 'PRODUCT NAME', font_bold)
        # worksheet.write(8, 4, 'BRAND NAME', font_bold)
        worksheet.write(8, 4, 'QUANTITY', font_bold)
        worksheet.write(8, 5, 'SALES PRICE', font_bold)
        worksheet.write(8, 6, 'SALES AMOUNT', font_bold)
        worksheet.write(8, 7, 'TAX', font_bold)
        worksheet.write(8, 8, 'UNIT COST', font_bold)
        worksheet.write(8, 9, 'TOTAL COST', font_bold)
        worksheet.write(8, 10, 'ADD COST', font_bold)
        worksheet.write(8, 11, 'GROSS PROFIT', font_bold)

        line_details = self.get_lines()
        i = 9
        total_qty = 0.0
        total_sale_amount = 0.0
        total_cost = 0.0
        total_gross_profit = 0.0
        total_tax_amount = 0.0
        total_total_cost = 0.0
        total_sale = 0.0
        if line_details:
            style_2 = easyxf('font:height 200; align: horiz right;')
            currency_format = company_id.currency_id.symbol + "#,##0.00"
            style_2.num_format_str = currency_format
            style_3 = easyxf('font:height 200; align: horiz right;')
            style_3.num_format_str = '0.00'

            for line in line_details:
                worksheet.row(i).height = 20 * 25
                total_qty += line.get('qty')
                total_sale_amount +=  line.get('sale_amount')
                total_sale +=  line.get('sale')
                total_tax_amount +=  line.get('tax_amount')
                total_cost += line.get('cost')
                total_total_cost += line.get('total_cost')
                total_gross_profit += line.get('gross_profit')

                worksheet.write(i, 0,line.get('date'),easyxf('align: horiz center;'))
                worksheet.write(i, 1, line.get('name', '') ,easyxf('align: horiz center;'))
                worksheet.write(i, 2, line.get('suppliers', '') ,easyxf('align: horiz center;'))
                worksheet.write(i, 3, line.get('product_name', '') ,easyxf('align: horiz center;'))
                # worksheet.write(i, 4, line.get('brand_name', '') ,easyxf('align: horiz center;'))
                worksheet.write(i, 4, line.get('qty', 0.0), style_3)
                worksheet.write(i, 5, line.get('sale', 0.0), style_3)
                worksheet.write(i, 6, line.get('sale_amount', 0.0), style_3)
                worksheet.write(i, 7, line.get('tax_amount', 0.0), style_3)
                worksheet.write(i, 8, line.get('cost', 0.0), style_3)
                worksheet.write(i, 9, line.get('total_cost', 0.0), style_3)
                worksheet.write(i, 10, float(0), style_3)
                worksheet.write(i, 11, line.get('gross_profit', 0.0), style_3)
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
        worksheet.write(i, 4, total_qty, foolter_style_1)
        worksheet.write(i, 5, total_sale, foolter_style_1)
        worksheet.write(i, 6, total_sale_amount, foolter_style_1)
        worksheet.write(i, 7, total_tax_amount, foolter_style_1)
        worksheet.write(i, 8, total_cost, foolter_style_1)
        worksheet.write(i, 9, total_total_cost, foolter_style_1)
        worksheet.write(i, 10, 0.0, foolter_style_1)
        worksheet.write(i, 11, total_gross_profit, foolter_style_1)
            
        import io
        fp = io.BytesIO()
        workbook.save(fp)
        export_id = self.env['pos.product.report'].create(
            {'excel_file': base64.encodestring(fp.getvalue()),
             'file_name': filename},)
        fp.close()
        
        return {
            'view_mode': 'form',
            'res_id': export_id.id,
            'res_model': 'pos.product.report',
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
        return self.env.ref('mai_pos_advance_report.action_print_product_clonet').report_action([], data=datas)

class pos_product_report_download(models.TransientModel):
    _name = "pos.product.report"
    
    excel_file = fields.Binary('Excel Report')
    file_name = fields.Char('Excel File', size=64)