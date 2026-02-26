from odoo import models, fields

class BiSalesFilterWizard(models.TransientModel):
    _name = 'wizard.bi.sales.filter'

    start_date = fields.Date("Start Date")
    end_date = fields.Date("End Date")
    team_id = fields.Many2one("crm.team", string="Sales Team")

    def open_report(self):
        domain = []
        if self.start_date:
            domain.append(('x_order_date', '>=', self.start_date))
        if self.end_date:
            domain.append(('x_order_date', '<=', self.end_date))
        if self.team_id:
            domain.append(('x_sales_team', '=', self.team_id.name))

        return {
            'type': 'ir.actions.act_window',
            'name': 'Sales Summary',
            'res_model': 'bi.sales.summary.mv',
            'view_mode': 'tree,pivot',
            'domain': domain,
        }
