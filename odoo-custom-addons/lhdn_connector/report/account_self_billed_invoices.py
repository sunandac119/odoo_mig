from odoo import models, fields, api

class ReportInvoiceWithPayment(models.AbstractModel):
    _name = 'report.lhdn_connector.report_self_billed_invoices'
    _description = 'Accounts Self Billed report'
    _inherit = 'report.account.report_invoice'

    @api.model
    def _get_report_values(self, docids, data=None):
        rslt = super()._get_report_values(docids, data)
        rslt['report_type'] = data.get('report_type') if data else ''
        return rslt