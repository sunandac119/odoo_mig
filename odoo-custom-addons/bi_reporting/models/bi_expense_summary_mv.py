from odoo import models, fields

class BiExpenseSummaryMV(models.Model):
    _name = 'bi.expense.summary.mv'
    _description = 'BI Expense Summary'
    _auto = False

    x_expense_date = fields.Date("Expense Date")
    x_team = fields.Char("Sales Team")
    x_expense_name = fields.Char("Expense Description")
    x_total_amount = fields.Float("Amount")

    def refresh_view(self):
        self.env.cr.execute("REFRESH MATERIALIZED VIEW bi_expense_summary_mv")
