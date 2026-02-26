from odoo import models, fields, api

class WizardSalesSummaryMV(models.TransientModel):
    _name = 'wizard.sales.summary.mv'
    _description = 'Sales Summary Filter Wizard'

    start_date = fields.Date('Start Date', required=True)
    end_date = fields.Date('End Date', required=True)
    vendor_id = fields.Many2one('res.partner', string='Vendor')
    product_categ_id = fields.Many2one('product.category', string='Product Category')
    sale_team_id = fields.Many2one('crm.team', string='Sales Team')

    def action_view_filtered_report(self):
        domain = [('x_order_date', '>=', self.start_date), ('x_order_date', '<=', self.end_date)]
        if self.vendor_id:
            domain.append(('x_vendor_name', '=', self.vendor_id.name))
        if self.product_categ_id:
            domain.append(('x_product_categ', '=', self.product_categ_id.name))
        if self.sale_team_id:
            domain.append(('x_sales_team', '=', self.sale_team_id.name))

        return {
            'name': 'Filtered Sales Summary',
            'type': 'ir.actions.act_window',
            'res_model': 'bi.sales.summary.mv',
            'view_mode': 'tree,pivot',
            'domain': domain,
            'target': 'current',
        }
