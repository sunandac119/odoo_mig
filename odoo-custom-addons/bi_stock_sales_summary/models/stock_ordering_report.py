from odoo import models, fields

class BiOrderingReportMV(models.Model):
    _name = 'bi.ordering.report.mv'
    _description = 'BI Stock Ordering Materialized View'
    _auto = False
    _table = 'bi_ordering_report_mv'

    product_tmpl_id = fields.Many2one('product.template', string='Product')
    x_product_name = fields.Char(string='Product Name')
    x_parent_product_name = fields.Char(string='Parent Product Name')
    x_product_categ = fields.Char(string='Product Category')
    x_total_sold_qty = fields.Float(string='Total Sold Qty (90d)')
    x_total_sales = fields.Float(string='Total Sales Amount (90d)')

    def init(self):
        self.env.cr.execute("""
            CREATE MATERIALIZED VIEW IF NOT EXISTS bi_ordering_report_mv AS
            WITH sale_summary AS (
                SELECT
                    pp.id AS product_id,
                    pt.id AS product_tmpl_id,
                    SUM(sr.product_uom_qty) FILTER (WHERE sr.state NOT IN ('draft', 'cancel')) AS sale_qty,
                    SUM(sr.price_total) FILTER (WHERE sr.state NOT IN ('draft', 'cancel')) AS sale_amount
                FROM sale_report sr
                JOIN product_product pp ON sr.product_id = pp.id
                JOIN product_template pt ON pp.product_tmpl_id = pt.id
                WHERE sr.date >= (current_date - INTERVAL '90 days')
                GROUP BY pp.id, pt.id
            ),
            pos_summary AS (
                SELECT
                    pol.product_id,
                    pt.id AS product_tmpl_id,
                    SUM(pol.qty) AS pos_qty,
                    SUM(pol.price_subtotal_incl) AS pos_amount
                FROM pos_order_line pol
                JOIN pos_order po ON pol.order_id = po.id
                JOIN product_product pp ON pol.product_id = pp.id
                JOIN product_template pt ON pp.product_tmpl_id = pt.id
                WHERE po.date_order >= (current_date - INTERVAL '90 days')
                GROUP BY pol.product_id, pt.id
            ),
            combined_sales AS (
                SELECT
                    COALESCE(s.product_id, p.product_id) AS product_id,
                    COALESCE(s.product_tmpl_id, p.product_tmpl_id) AS product_tmpl_id,
                    COALESCE(s.sale_qty, 0) + COALESCE(p.pos_qty, 0) AS total_sold_qty,
                    COALESCE(s.sale_amount, 0) + COALESCE(p.pos_amount, 0) AS total_sales
                FROM sale_summary s
                FULL OUTER JOIN pos_summary p ON s.product_id = p.product_id
            )
            SELECT
                row_number() OVER () AS id,
                pt.id AS product_tmpl_id,
                pt.name AS x_product_name,
                parent_pt.name AS x_parent_product_name,
                pc.name AS x_product_categ,
                COALESCE(cs.total_sold_qty, 0) AS x_total_sold_qty,
                COALESCE(cs.total_sales, 0) AS x_total_sales
            FROM product_template pt
            LEFT JOIN product_template parent_pt ON pt.parent_template_id = parent_pt.id
            LEFT JOIN product_category pc ON pt.categ_id = pc.id
            LEFT JOIN combined_sales cs ON cs.product_tmpl_id = pt.id;
        """)
