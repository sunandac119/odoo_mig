from odoo import models, fields

class LowSalesReportMV(models.Model):
    _name = "low.sales.report.mv"
    _auto = False
    _description = "Low Sales Report Materialized View"

    product_id = fields.Many2one('product.product', string='Product', readonly=True)
    product_name = fields.Char('Product Name', readonly=True)
    warehouse_id = fields.Many2one('stock.warehouse', string='Warehouse', readonly=True)
    warehouse_name = fields.Char('Warehouse Name', readonly=True)
    total_unit_qty_sold = fields.Float('Sale Unit Qty', readonly=True)
    sale_ctn_qty = fields.Float('Sale Carton Qty', readonly=True)
    total_revenue = fields.Float('Revenue', readonly=True)
    unit_price = fields.Float('Unit Price', readonly=True)   # 🟰 ADD THIS LINE

    def init(self):
        self.env.cr.execute(f"DROP MATERIALIZED VIEW IF EXISTS {self._table} CASCADE")
        self.env.cr.execute(f"""
            CREATE MATERIALIZED VIEW {self._table} AS (
                SELECT
                    row_number() OVER () AS id,
                    sol.product_id,
                    pt.name AS product_name,
                    wh.id AS warehouse_id,
                    wh.name AS warehouse_name,
                    SUM(sol.product_uom_qty) AS total_unit_qty_sold,
                    CASE WHEN pt.ctn_qty > 0 THEN SUM(sol.product_uom_qty)/pt.ctn_qty ELSE 0 END AS sale_ctn_qty,
                    SUM(sol.product_uom_qty * sol.price_unit) AS total_revenue,
                    CASE WHEN SUM(sol.product_uom_qty) > 0 THEN SUM(sol.product_uom_qty * sol.price_unit) / SUM(sol.product_uom_qty) ELSE 0 END AS unit_price
                FROM
                    sale_order_line sol
                    JOIN sale_order so ON so.id = sol.order_id
                    JOIN product_product pp ON pp.id = sol.product_id
                    JOIN product_template pt ON pt.id = pp.product_tmpl_id
                    JOIN stock_warehouse wh ON so.warehouse_id = wh.id
                WHERE
                    sol.display_type IS NULL
                    AND pt.active=true
                GROUP BY
                    sol.product_id, pt.name, wh.id, wh.name, pt.ctn_qty
            )
        """)

    def refresh_mv(self):
        self.env.cr.execute(f"REFRESH MATERIALIZED VIEW {self._table}")
