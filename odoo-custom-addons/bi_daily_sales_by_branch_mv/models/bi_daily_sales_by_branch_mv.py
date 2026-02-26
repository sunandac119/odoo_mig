from odoo import models, fields

class BiDailySalesByBranchMV(models.Model):
    _name = "bi.daily.sales.by.branch.mv"
    _description = "BI Daily Sales by Branch"
    _auto = False
    _rec_name = "order_date"

    order_date = fields.Date(string="Order Date")
    branch_id = fields.Many2one("res.branch", string="Branch")
    total_sales = fields.Float(string="Total Sales")
    order_count = fields.Integer(string="Order Count")
    orderline_qty = fields.Integer(string="Order Line Qty")
    avg_sales_per_order = fields.Float(string="Avg Sales/Order")
    basket_size = fields.Float(string="Basket Size")
