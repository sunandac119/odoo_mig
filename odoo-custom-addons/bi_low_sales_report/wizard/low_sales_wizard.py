# -*- coding: utf-8 -*-
# Part of BrowseInfo. See LICENSE file for full copyright and licensing details.

from odoo import fields, models, api, _
from odoo.exceptions import UserError, ValidationError
from datetime import datetime
import xlsxwriter
import base64
import io
from io import BytesIO
import xlwt
import csv

class LowSalesReportWizard(models.TransientModel):
    _name = "low.sales.report"
    _description = "Low Sales Report"

    report_type = fields.Selection([('product', 'Product'),
                                ('product_variant', 'Product Variant'),
                                ('product_category', 'Product Category'),
                                ], string='Report Type', required=True, default='product')
    all_product = fields.Boolean(string = "All")
    product_ids = fields.Many2many('product.template',string="Product")
    product_category_ids= fields.Many2many('product.category',string="Product Category")
    product_variant_ids= fields.Many2many('product.product',string="Product Variant")
    order_line_ids = fields.Many2many('sale.order.line',string="line")
    date_from = fields.Date('Start Date',required="True")
    date_to = fields.Date('End Date',required="True")
    quantity = fields.Float('Quantity', required="True")
    amount = fields.Float('Amount',required="True")


    @api.constrains('date_from', 'date_to')
    def _check_dates(self):
        for record in self:
            if record.date_from and record.date_to:
                if record.date_to < record.date_from:
                    raise ValidationError("End date must be greater than start date!")

    @api.constrains('quantity', 'amount')
    def _check_quantity_amount(self):
        for record in self:
            if record.quantity <= 0.00 or record.amount <= 0.00:
                raise ValidationError("Quantity and Amount is greater than 0.0 !")


    @api.model
    def default_get(self, default_fields):
        res = super(LowSalesReportWizard, self).default_get(default_fields)
        data = self.env['res.config.settings'].sudo().search([],order="id desc", limit=1)
        update = []
        for record in data:
            res.update({
                'quantity':data.quantity,
                'amount':data.amount,
            })
        return res

    def low_sales_pdf_report(self):
        [data] = self.read()
        datas = {
             'ids': [1],
             'model': 'low.sales.reports',
             'form': data
        }
        action = self.env.ref('bi_low_sales_report.low_sales_report_action_view').report_action(self, data=datas)
        return action


    def low_sales_xls(self):
        data ={
                'form': self.read()[0],
             
        }
        filename = 'Low Sales Report.xls'
        workbook = xlwt.Workbook()
        worksheet = workbook.add_sheet('Sheet 1')
        worksheet.col(0).width = 5000
        style_header = xlwt.easyxf(
            "font:height 300; font: name Liberation Sans, bold on,color black; align: vert centre, horiz center;pattern: pattern solid, pattern_fore_colour gray25;")

        style_line_heading = xlwt.easyxf("font: name Liberation Sans, bold on;align: horiz centre; pattern: pattern solid, pattern_fore_colour gray25;")
        worksheet.row(0).height_mismatch = True
        worksheet.row(0).height = 500
        if self.report_type == 'product':
            worksheet.write_merge(0, 1, 0, 5, "Low Sales Report - Product\n"+str(self.date_from.strftime('%d-%m-%Y')) + ' To ' + str(self.date_to.strftime('%d-%m-%Y')), style=style_header)
        elif self.report_type == 'product_variant':
            worksheet.write_merge(0, 1, 0, 5, "Low Sales Report - Product Variant\n"+str(self.date_from.strftime('%d-%m-%Y')) + ' To ' + str(self.date_to.strftime('%d-%m-%Y')), style=style_header)
        else: 
            worksheet.write_merge(0, 1, 0, 5, "Low Sales Report - Product Category\n"+str(self.date_from.strftime('%d-%m-%Y')) + ' To ' + str(self.date_to.strftime('%d-%m-%Y')), style=style_header)
        line = 3
        for i in data:
            worksheet.write(line,0, 'Sr No', style = style_line_heading)
            worksheet.write(line,1, 'Internal Reference', style = style_line_heading)
            worksheet.write(line,2, 'Product Name', style = style_line_heading)
            worksheet.write(line,3, 'Quantity', style = style_line_heading)
            worksheet.write(line,4, 'Unit Price', style = style_line_heading)
            worksheet.write(line,5, 'Revenue', style = style_line_heading)

        line = 4
        counter = 1
        product_template_ids = self.env['product.template'].search([])
        product_ids = self.env['product.product'].search([])
        product_category_ids = self.env['product.category'].search([('id','in',self.product_category_ids.ids)])

        order_line_lst = []
        if self.report_type == 'product':
            for product in product_template_ids:
                order_line_ids = self.env['sale.order.line'].search([('order_id.date_order','>=',self.date_from),('order_id.date_order','<=',self.date_to),('product_id.product_tmpl_id','in',product.ids)])
                product_qty_sum = sum([line.product_uom_qty for line in order_line_ids])
                price_unit_sum = sum([line.price_unit for line in order_line_ids])
                revenu_total = product_qty_sum * price_unit_sum
                order_line_lst.append({'product': product, 'quantity': product_qty_sum, 'total_revenue': revenu_total,'price_unit': price_unit_sum,})
        
        elif self.report_type == 'product_variant':
            for product in product_ids:
                order_line_ids = self.env['sale.order.line'].search([('order_id.date_order','>=',self.date_from),('order_id.date_order','<=',self.date_to),('product_id','in',product.ids)])
                product_qty_sum = sum([line.product_uom_qty for line in order_line_ids])
                price_unit_sum = sum([line.price_unit for line in order_line_ids])
                revenu_total = product_qty_sum * price_unit_sum
                order_line_lst.append({'product': product, 'quantity': product_qty_sum, 'total_revenue': revenu_total,'price_unit': price_unit_sum})

        elif self.report_type == 'product_category':
            if product_category_ids:
                for product in product_ids.filtered(lambda a: a.categ_id.id in product_category_ids.ids):
                    order_line_ids = self.env['sale.order.line'].search([('order_id.date_order','>=',self.date_from),('order_id.date_order','<=',self.date_to),('product_id','in',product.ids)])
                    product_qty_sum = sum([line.product_uom_qty for line in order_line_ids])
                    price_unit_sum = sum([line.price_unit for line in order_line_ids])
                    revenu_total = product_qty_sum * price_unit_sum
                    order_line_lst.append({'product': product, 'quantity': product_qty_sum, 'total_revenue': revenu_total,'price_unit': price_unit_sum})

        for rec in order_line_lst:
            worksheet.write(line, 0, counter, style=xlwt.easyxf("font: name Liberation Sans; align: horiz center;"))   
            worksheet.write(line, 1, rec['product'].default_code, style=xlwt.easyxf("font: name Liberation Sans; align: horiz center;"))
            worksheet.write(line, 2, rec['product'].name, style=xlwt.easyxf("font: name Liberation Sans; align: horiz center;"))
            if self.quantity > rec['quantity'] and self.amount > rec['product'].list_price: 
                worksheet.write(line, 3, rec['quantity'], style=xlwt.easyxf("font: name Liberation Sans; align: horiz center;"))
                worksheet.write(line, 4, rec['price_unit'], style=xlwt.easyxf("font: name Liberation Sans; align: horiz center;"))
                worksheet.write(line, 5, rec['total_revenue'], style=xlwt.easyxf("font: name Liberation Sans; align: horiz center;"))
            else:
                worksheet.write(line, 3, 0.0, style=xlwt.easyxf("font: name Liberation Sans; align: horiz center;"))
                worksheet.write(line, 4, 0.0, style=xlwt.easyxf("font: name Liberation Sans; align: horiz center;"))
                worksheet.write(line, 5, 0.0, style=xlwt.easyxf("font: name Liberation Sans; align: horiz center;"))
            line = line+1
            counter = counter + 1
        fp = io.BytesIO()
        workbook.save(fp)

        export_id = self.env['excel.report'].create(
            {'excel_file': base64.encodebytes(fp.getvalue()), 'file_name': filename})
        res = {
            'view_mode': 'form',
            'res_id': export_id.id,
            'res_model': 'excel.report',
            'view_type': 'form',
            'type': 'ir.actions.act_window',
            'target': 'new'
        }
        return res