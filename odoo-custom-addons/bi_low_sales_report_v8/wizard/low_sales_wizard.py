
from odoo import models, fields, api

class LowSalesWizard(models.TransientModel):
    _name = "low.sales.report.wizard"
    _description = "Low Sales Report Wizard"

    date_from = fields.Date('Date From', required=True)
    date_to = fields.Date('Date To', required=True)
    warehouse_id = fields.Many2one('stock.warehouse', string='Warehouse')

    def action_open_report(self):
        domain = [('total_unit_qty_sold', '<=', 10)]
        if self.warehouse_id:
            domain.append(('warehouse_id', '=', self.warehouse_id.id))
        return {
            'name': 'Low Sales Pivot',
            'view_mode': 'pivot',
            'res_model': 'low.sales.report.mv',
            'type': 'ir.actions.act_window',
            'domain': domain,
            'context': dict(self.env.context),
        }
