from odoo import models, fields
import logging

_logger = logging.getLogger(__name__)

class BiSalesSummaryMV(models.Model):
    _name = 'bi.sales.summary.mv'
    _description = 'BI Sales Summary Materialized View'
    _auto = False
    _table = 'bi_sales_summary_mv'

    x_vendor_name = fields.Char('Vendor')
    x_sales_team = fields.Char('Sales Team')
    x_product_name = fields.Char('Product')
    x_parent_product_name = fields.Char('Parent Product')
    x_order_date = fields.Date('Order Date')
    x_pos_qty = fields.Float('POS Qty')
    x_pos_sales = fields.Float('POS Sales')
    x_credit_qty = fields.Float('Credit Qty')
    x_credit_sales = fields.Float('Credit Sales')
    x_total_qty = fields.Float('Total Qty')
    x_total_sales = fields.Float('Total Sales')

    def init(self):
        self.env.cr.execute("""
            CREATE MATERIALIZED VIEW IF NOT EXISTS bi_sales_summary_mv AS
            SELECT
                row_number() OVER () AS id,
                COALESCE(rp.name, 'No Vendor') AS x_vendor_name,
                COALESCE(st.name, 'No Sales Team') AS x_sales_team,
                COALESCE(pt.name, 'No Product') AS x_product_name,
                COALESCE(parent_pt.name, 'No Parent') AS x_parent_product_name,
                sr.date::date AS x_order_date,
                SUM(sr.product_uom_qty) FILTER (WHERE sr.state NOT IN ('draft', 'cancel')) AS x_pos_qty,
                SUM(sr.price_total) FILTER (WHERE sr.state NOT IN ('draft', 'cancel')) AS x_pos_sales,
                SUM(sr.product_uom_qty) FILTER (WHERE sr.state = 'sale') AS x_credit_qty,
                SUM(sr.price_total) FILTER (WHERE sr.state = 'sale') AS x_credit_sales,
                SUM(sr.product_uom_qty) AS x_total_qty,
                SUM(sr.price_total) AS x_total_sales
            FROM sale_report sr
            LEFT JOIN product_product pp ON sr.product_id = pp.id
            LEFT JOIN product_template pt ON pp.product_tmpl_id = pt.id
            LEFT JOIN product_template parent_pt ON pt.parent_template_id = parent_pt.id
            LEFT JOIN product_supplierinfo psi ON pt.id = psi.product_tmpl_id
            LEFT JOIN res_partner rp ON psi.name = rp.id
            LEFT JOIN crm_team st ON sr.team_id = st.id
            WHERE sr.date >= (current_date - INTERVAL '90 days')
            GROUP BY rp.name, st.name, pt.name, parent_pt.name, sr.date::date;
        """)
