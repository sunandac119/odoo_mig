
from odoo import fields, models, api, _
from odoo.exceptions import ValidationError
import xlwt
import base64
import io

class LowSalesReportWizard(models.TransientModel):
    _name = "low.sales.report"
    _description = "Low Sales Report"

    report_type = fields.Selection([
        ('product', 'Product'),
        ('product_variant', 'Product Variant'),
        ('product_category', 'Product Category'),
    ], string='Report Type', required=True, default='product')

    all_product = fields.Boolean(string="All")
    product_ids = fields.Many2many('product.template', string="Products")
    product_variant_ids = fields.Many2many('product.product', string="Product Variants")
    product_category_ids = fields.Many2many('product.category', string="Product Categories")
    warehouse_id = fields.Many2one('stock.warehouse', string='Warehouse', required=True)
    date_from = fields.Date('Start Date', required=True)
    date_to = fields.Date('End Date', required=True)
    quantity = fields.Float('Max Carton Quantity', required=True)
    amount = fields.Float('Max Total Revenue', required=True)

    @api.constrains('date_from', 'date_to')
    def _check_dates(self):
        for record in self:
            if record.date_to < record.date_from:
                raise ValidationError("End date must be greater than start date!")

    def low_sales_xls(self):
        domain = [
            ('warehouse_id', '=', self.warehouse_id.id),
            ('sale_ctn_qty', '<=', self.quantity),
            ('total_revenue', '<=', self.amount)
        ]
        low_sales = self.env['low.sales.report.mv'].search(domain)

        filename = 'Low_Sales_Report.xls'
        workbook = xlwt.Workbook()
        sheet = workbook.add_sheet('Low Sales')

        header_style = xlwt.easyxf(
            "font:height 300; font: name Liberation Sans, bold on, color black; align: vert centre, horiz center;"
            "pattern: pattern solid, pattern_fore_colour gray25;")
        text_style = xlwt.easyxf("font: name Liberation Sans; align: horiz center;")

        sheet.write_merge(0, 1, 0, 6, "Low Sales Report", header_style)
        headers = ['Sr No', 'Internal Reference', 'Product Name', 'Warehouse', 'Sale Unit Qty', 'Sale Carton Qty', 'Total Revenue']
        for idx, val in enumerate(headers):
            sheet.write(2, idx, val, header_style)

        line = 3
        counter = 1
        for rec in low_sales:
            sheet.write(line, 0, counter, text_style)
            sheet.write(line, 1, rec.internal_reference or '', text_style)
            sheet.write(line, 2, rec.product_name, text_style)
            sheet.write(line, 3, rec.warehouse_name, text_style)
            sheet.write(line, 4, round(rec.total_unit_qty_sold, 2), text_style)
            sheet.write(line, 5, round(rec.sale_ctn_qty, 2), text_style)
            sheet.write(line, 6, round(rec.total_revenue, 2), text_style)
            line += 1
            counter += 1

        fp = io.BytesIO()
        workbook.save(fp)

        export_id = self.env['excel.report'].create({
            'excel_file': base64.encodebytes(fp.getvalue()),
            'file_name': filename
        })

        return {
            'view_mode': 'form',
            'res_id': export_id.id,
            'res_model': 'excel.report',
            'view_type': 'form',
            'type': 'ir.actions.act_window',
            'target': 'new'
        }
