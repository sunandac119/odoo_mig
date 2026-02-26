
from odoo import fields, models, tools, api

class LowSalesReportMV(models.Model):
    _name = 'low.sales.report.mv'
    _description = 'Low Sales Report Materialized View'
    _auto = False

    product_id = fields.Many2one('product.product', string='Product', readonly=True)
    internal_reference = fields.Char('Internal Reference', readonly=True)
    product_name = fields.Char('Product Name', readonly=True)
    warehouse_id = fields.Many2one('stock.warehouse', string='Warehouse', readonly=True)
    warehouse_name = fields.Char('Warehouse Name', readonly=True)
    total_unit_qty_sold = fields.Float('Total Unit Quantity Sold', readonly=True)
    sale_ctn_qty = fields.Float('Sale Carton Quantity (From Sale Qty)', readonly=True)
    ctn_qty_sold = fields.Float('Carton Quantity Sold (From Ctn Unit)', readonly=True)
    avg_unit_price = fields.Float('Average Unit Price', readonly=True)
    total_revenue = fields.Float('Total Revenue', readonly=True)

    def init(self):
        tools.drop_view_if_exists(self.env.cr, self._table)
        self.env.cr.execute("""
            CREATE MATERIALIZED VIEW %s AS
            SELECT
                row_number() OVER () AS id,
                p.id AS product_id,
                p.default_code AS internal_reference,
                p.name AS product_name,
                w.id AS warehouse_id,
                w.name AS warehouse_name,
                SUM(l.product_uom_qty) AS total_unit_qty_sold,
                CASE WHEN t.ctn_unit > 0 THEN SUM(l.product_uom_qty) / t.ctn_unit ELSE 0 END AS sale_ctn_qty,
                CASE WHEN t.ctn_unit > 0 THEN SUM(l.product_uom_qty) / t.ctn_unit ELSE 0 END AS ctn_qty_sold,
                CASE WHEN SUM(l.product_uom_qty) > 0 THEN SUM(l.price_subtotal) / SUM(l.product_uom_qty) ELSE 0 END AS avg_unit_price,
                SUM(l.price_subtotal) AS total_revenue
            FROM
                sale_order_line l
            LEFT JOIN
                sale_order s ON s.id = l.order_id
            LEFT JOIN
                stock_warehouse w ON w.id = s.warehouse_id
            LEFT JOIN
                product_product p ON p.id = l.product_id
            LEFT JOIN
                product_template t ON p.product_tmpl_id = t.id
            WHERE
                l.display_type IS NULL
                AND s.state IN ('sale', 'done')
            GROUP BY
                p.id, p.default_code, p.name, t.ctn_unit, w.id, w.name
        """ % self._table)

class LowSalesReportMVRefresh(models.Model):
    _name = 'low.sales.report.mv.refresh'
    _description = 'Refresh Low Sales Report Materialized View'

    @api.model
    def refresh_mv(self):
        self.env.cr.execute('REFRESH MATERIALIZED VIEW CONCURRENTLY low_sales_report_mv;')
