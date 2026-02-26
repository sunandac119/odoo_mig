from odoo import models, api, fields, _
from odoo.exceptions import ValidationError
import xlsxwriter
import base64
from datetime import timedelta
from odoo.tools.misc import formatLang


class WizardInventoryValuationQty(models.TransientModel):
    _name = 'wizard.inventory.valuation.qty'
    _description = 'Inventory Valuation Report Wizard'

    company_id = fields.Many2one('res.company', string='Company', default=lambda self: self.env.user.company_id.id)
    warehouse_ids = fields.Many2many('stock.warehouse', string='Warehouse')
    location_ids = fields.Many2many('stock.location', string='Location')
    start_date = fields.Date(string="Start Date")
    end_date = fields.Date(string="End Date", default=fields.Date.context_today)
    filter_by = fields.Selection([('product', 'Product'), ('category', 'Category')], string="Filter By")
    group_by_categ = fields.Boolean(string="Group By Category")
    state = fields.Selection([('choose', 'Choose'), ('get', 'Get')], default='choose')
    name = fields.Char(string='File Name', readonly=True)
    data = fields.Binary(string='File', readonly=True)
    product_ids = fields.Many2many('product.product', string="Products")
    seller_ids = fields.Many2many('res.partner', string="Vendors")
    category_ids = fields.Many2many('product.category', string="Categories")
    suggestion = fields.Integer(string='Suggestion (Days)', default=37)

    @api.onchange('seller_ids')
    def onchange_seller_ids(self):
        self.product_ids = [(5,)]  # Clear products
        if self.seller_ids:
            supplierinfo_obj = self.env['product.supplierinfo'].search([
                ('name', 'in', self.seller_ids.ids),
                ('sequence', '=', 1),  # Only default vendor
            ])
            product_templates = supplierinfo_obj.mapped('product_tmpl_id')
            products = self.env['product.product'].search([
                ('type', '=', 'product'),
                ('product_tmpl_id', 'in', product_templates.ids),
            ])
            self.product_ids = [(6, 0, products.ids)] if products else []

    @api.onchange('company_id')
    def onchange_company_id(self):
        domain = [('id', 'in', self.env.user.company_ids.ids)]
        if self.company_id:
            self.warehouse_ids = False
            self.location_ids = False
        return {'domain': {'company_id': domain}}

    @api.onchange('warehouse_ids')
    def onchange_warehouse_ids(self):
        stock_location_obj = self.env['stock.location']
        location_ids = stock_location_obj.search([('usage', '=', 'internal'), ('company_id', '=', self.company_id.id)])
        additional_ids = []
        if self.warehouse_ids:
            for warehouse in self.warehouse_ids:
                additional_ids.extend(
                    stock_location_obj.search(
                        [('location_id', 'child_of', warehouse.view_location_id.id), ('usage', '=', 'internal')]
                    ).ids
                )
            self.location_ids = False
        return {'domain': {'location_ids': [('id', 'in', additional_ids)]}}

    @api.onchange('suggestion')
    def onchange_suggestion(self):
        if self.suggestion is not None:
            self.end_date = fields.Date.context_today(self)
            self.start_date = self.end_date - timedelta(days=self.suggestion)

    def check_date_range(self):
        if self.start_date and self.end_date and self.end_date < self.start_date:
            raise ValidationError(_('End Date should be greater than Start Date.'))

    def print_report(self):
        self.check_date_range()
        datas = {'form': {
            'company_id': self.company_id.id,
            'warehouse_ids': [w.id for w in self.warehouse_ids],
            'location_ids': self.location_ids.ids or False,
            'start_date': self.start_date,
            'end_date': self.end_date,
            'id': self.id,
            'seller_ids': self.seller_ids.ids,
            'product_ids': self.product_ids.ids,
            'product_categ_ids': self.category_ids.ids,
        }}
        return self.env.ref('order_report.action_inventory_valuation_template').report_action(self, data=datas)

    def go_back(self):
        self.state = 'choose'
        return {
            'name': 'Inventory Valuation Report',
            'type': 'ir.actions.act_window',
            'res_model': self._name,
            'view_mode': 'form',
            'view_type': 'form',
            'res_id': self.id,
            'target': 'new'
        }

    def print_xls_report(self):
        self.check_date_range()
        xls_filename = 'inventory_valuation_report.xlsx'
        tmp_file = '/tmp/' + xls_filename
        workbook = xlsxwriter.Workbook(tmp_file)
        report_stock_inv_obj = self.env['report.order_report.inventory_valuation_report']

        header_merge_format = workbook.add_format({'bold': True, 'align': 'center', 'valign': 'vcenter',
                                                   'font_size': 10, 'bg_color': '#D3D3D3', 'border': 1})
        header_data_format = workbook.add_format({'align': 'center', 'valign': 'vcenter',
                                                  'font_size': 10, 'border': 1})
        product_header_format = workbook.add_format({'valign': 'vcenter', 'font_size': 10, 'border': 1})
        total_format = workbook.add_format({'bold': True, 'align': 'center', 'valign': 'vcenter',
                                             'font_size': 10, 'border': 1, 'bg_color': '#F4B084'})

        for warehouse in self.warehouse_ids:
            worksheet = workbook.add_worksheet(warehouse.name)
            worksheet.merge_range(0, 0, 2, 8, "Inventory Valuation Report", header_merge_format)

            worksheet.set_column('A:B', 20)
            worksheet.set_column('C:C', 15)
            worksheet.set_column('D:H', 12)

            worksheet.write(5, 0, 'Company', header_merge_format)
            worksheet.write(5, 1, 'Warehouse', header_merge_format)
            worksheet.write(5, 2, 'Start Date', header_merge_format)
            worksheet.write(5, 3, 'End Date', header_merge_format)

            worksheet.write(6, 0, self.company_id.name, header_data_format)
            worksheet.write(6, 1, warehouse.name, header_data_format)
            worksheet.write(6, 2, str(self.start_date), header_data_format)
            worksheet.write(6, 3, str(self.end_date), header_data_format)

            worksheet.merge_range(9, 0, 9, 1, "Products", header_merge_format)
            worksheet.write(9, 2, "Costing Method", header_merge_format)
            worksheet.merge_range(9, 3, 9, 4, "Beginning", header_merge_format)
            worksheet.merge_range(9, 5, 9, 6, "Received", header_merge_format)
            worksheet.merge_range(9, 7, 9, 8, "Sales", header_merge_format)
            worksheet.merge_range(9, 9, 9, 10, "Internal", header_merge_format)
            worksheet.merge_range(9, 11, 9, 12, "Adjustments", header_merge_format)
            worksheet.merge_range(9, 13, 9, 14, "Ending", header_merge_format)

            worksheet.write(10, 3, "Qty", header_merge_format)
            worksheet.write(10, 4, "Value", header_merge_format)
            worksheet.write(10, 5, "Qty", header_merge_format)
            worksheet.write(10, 6, "Value", header_merge_format)
            worksheet.write(10, 7, "Qty", header_merge_format)
            worksheet.write(10, 8, "Value", header_merge_format)
            worksheet.write(10, 9, "Qty", header_merge_format)
            worksheet.write(10, 10, "Value", header_merge_format)
            worksheet.write(10, 11, "Qty", header_merge_format)
            worksheet.write(10, 12, "Value", header_merge_format)
            worksheet.write(10, 13, "Qty", header_merge_format)
            worksheet.write(10, 14, "Value", header_merge_format)

            # Freeze header
            worksheet.freeze_panes(11, 0)

            rows = 11
            for product in report_stock_inv_obj._get_products(self):
                # Assume _get_products, get_product_valuation etc. are already working methods
                worksheet.merge_range(rows, 0, rows, 1, product.display_name, product_header_format)
                worksheet.write(rows, 2, product.categ_id.property_cost_method, header_data_format)
                # (Here you would write quantities and values by calling your helper methods)
                rows += 1

            worksheet.merge_range(rows, 0, rows, 2, 'Total', total_format)
            # (Here you would write sum of all quantities and values)

        workbook.close()

        self.write({
            'state': 'get',
            'data': base64.b64encode(open(tmp_file, 'rb').read()),
            'name': xls_filename
        })

        return {
            'name': 'Inventory Valuation Report',
            'type': 'ir.actions.act_window',
            'res_model': self._name,
            'view_mode': 'form',
            'view_type': 'form',
            'res_id': self.id,
            'target': 'new'
        }
