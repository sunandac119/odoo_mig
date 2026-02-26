from odoo import models, fields

class BiInventorySummaryMV(models.Model):
    _name = 'bi.inventory.summary.mv'
    _description = 'BI Inventory Summary'
    _auto = False

    x_date = fields.Date("Date")
    x_warehouse = fields.Char("Warehouse")
    x_product_name = fields.Char("Product")
    x_qty_in = fields.Float("Stock In")
    x_qty_out = fields.Float("Stock Out")
    x_qty_internal = fields.Float("Internal Move")
    x_qty_adjustment = fields.Float("Adjustment")

    def refresh_view(self):
        self.env.cr.execute("REFRESH MATERIALIZED VIEW bi_inventory_summary_mv")
