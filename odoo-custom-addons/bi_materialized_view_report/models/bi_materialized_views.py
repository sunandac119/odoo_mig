
# -*- coding: utf-8 -*-
from odoo import models, fields, api
import logging

_logger = logging.getLogger(__name__)

class BiMaterializedViewControl(models.Model):
    _name = 'bi.materialized.view'
    _description = 'BI Materialized View Control'
    _auto = True

    name = fields.Char('Name', default='BI Materialized View Controller')

    @api.model
    def create_materialized_view(self):
        try:
            self.env.cr.execute("""
                DROP MATERIALIZED VIEW IF EXISTS bi_sales_summary_mv;

                CREATE MATERIALIZED VIEW bi_sales_summary_mv AS
                SELECT
                    row_number() OVER () AS id,
                    COALESCE(rp.name, 'No Vendor') AS x_vendor_name,
                    COALESCE(st.name, 'No Sales Team') AS x_sales_team,
                    COALESCE(pt.name, 'No Product') AS x_product_name,
                    COALESCE(parent_pt.name, 'No Parent') AS x_parent_product_name,
                    COALESCE(pc.name, 'No Category') AS x_product_categ,
                    sr.date::date AS x_order_date,
                    SUM(sr.product_uom_qty) FILTER (WHERE sr.state = 'pos_done') AS x_pos_qty,
                    SUM(sr.price_total) FILTER (WHERE sr.state = 'pos_done') AS x_pos_sales,
                    SUM(sr.product_uom_qty) FILTER (WHERE sr.state = 'sale') AS x_credit_qty,
                    SUM(sr.price_total) FILTER (WHERE sr.state = 'sale') AS x_credit_sales,
                    SUM(sr.product_uom_qty) AS x_total_qty,
                    SUM(sr.price_total) AS x_total_sales,
                    ip.value_float AS x_cost_price,
                    ip.value_float * SUM(sr.product_uom_qty) AS x_total_cost,
                    SUM(sr.price_total) - ip.value_float * SUM(sr.product_uom_qty) AS x_profit,
                    CASE 
                        WHEN SUM(sr.price_total) > 0 AND ip.value_float IS NOT NULL THEN 
                            ROUND(((SUM(sr.price_total) - ip.value_float * SUM(sr.product_uom_qty)) / SUM(sr.price_total) * 100)::numeric, 2)
                        ELSE 0 
                    END AS x_margin_percentage
                FROM sale_report sr
                LEFT JOIN product_product pp ON sr.product_id = pp.id
                LEFT JOIN product_template pt ON pp.product_tmpl_id = pt.id
                LEFT JOIN product_template parent_pt ON pt.parent_template_id = parent_pt.id
                LEFT JOIN product_category pc ON pt.categ_id = pc.id
                LEFT JOIN product_supplierinfo psi ON pt.id = psi.product_tmpl_id
                LEFT JOIN res_partner rp ON psi.name = rp.id
                LEFT JOIN crm_team st ON sr.team_id = st.id
                LEFT JOIN ir_property ip ON ip.name = 'standard_price'
                    AND ip.res_id = 'product.product,' || pp.id::text
                WHERE sr.date >= date_trunc('month', current_date) - INTERVAL '11 months'
                  AND sr.date < date_trunc('month', current_date) + INTERVAL '1 month'
                GROUP BY
                    rp.name, st.name, pt.name, parent_pt.name, pc.name, sr.date::date, ip.value_float
                ORDER BY
                    st.name, rp.name, pt.name, sr.date::date;

                CREATE UNIQUE INDEX IF NOT EXISTS idx_bi_sales_summary_mv_id ON bi_sales_summary_mv(id);
            """)

            self.env.cr.execute("""
                CREATE MATERIALIZED VIEW IF NOT EXISTS bi_daily_user_location_summary_mv AS
                WITH sales AS (
                    SELECT
                        ru.x_studio_working_location AS user_working_location,
                        so.date_order::date AS order_date,
                        SUM(so.amount_total) AS total_sales
                    FROM sale_order so
                    JOIN res_users ru ON so.user_id = ru.id
                    WHERE so.state IN ('sale', 'done')
                      AND so.date_order >= (CURRENT_DATE - INTERVAL '1 year')
                    GROUP BY ru.x_studio_working_location, so.date_order::date
                ),
                purchases AS (
                    SELECT
                        ru.x_studio_working_location AS user_working_location,
                        po.date_order::date AS order_date,
                        SUM(po.amount_total) AS total_purchase
                    FROM purchase_order po
                    JOIN res_users ru ON po.user_id = ru.id
                    WHERE po.state IN ('purchase', 'done')
                      AND po.date_order >= (CURRENT_DATE - INTERVAL '1 year')
                    GROUP BY ru.x_studio_working_location, po.date_order::date
                ),
                expenses AS (
                    SELECT
                        ru.x_studio_working_location AS user_working_location,
                        am.date::date AS order_date,
                        SUM(aml.debit - aml.credit) AS total_expense
                    FROM account_move_line aml
                    JOIN account_move am ON aml.move_id = am.id
                    JOIN res_users ru ON am.create_uid = ru.id
                    JOIN account_journal aj ON am.journal_id = aj.id
                    WHERE aj.type IN ('purchase', 'cash')
                      AND am.date >= (CURRENT_DATE - INTERVAL '1 year')
                      AND aml.debit > 0
                    GROUP BY ru.x_studio_working_location, am.date::date
                )
                SELECT
                    row_number() OVER () AS id,
                    COALESCE(s.user_working_location, p.user_working_location, e.user_working_location) AS user_working_location,
                    COALESCE(s.order_date, p.order_date, e.order_date) AS order_date,
                    COALESCE(s.total_sales, 0) AS total_sales,
                    COALESCE(p.total_purchase, 0) AS total_purchase,
                    COALESCE(e.total_expense, 0) AS total_expense
                FROM sales s
                FULL OUTER JOIN purchases p
                    ON s.user_working_location = p.user_working_location AND s.order_date = p.order_date
                FULL OUTER JOIN expenses e
                    ON COALESCE(s.user_working_location, p.user_working_location) = e.user_working_location
                    AND COALESCE(s.order_date, p.order_date) = e.order_date
                ORDER BY user_working_location, order_date;
            """)

            self.env.cr.execute("""
                CREATE UNIQUE INDEX IF NOT EXISTS idx_bi_daily_user_location_summary_mv_id
                ON bi_daily_user_location_summary_mv(id);
            """)
            _logger.info("Materialized Views created or verified.")
            return {'status': 'success', 'message': 'Materialized Views created'}
        except Exception as e:
            _logger.error(f"Failed to create Materialized Views: {str(e)}")
            return {'status': 'error', 'message': str(e)}

    @api.model
    def refresh_materialized_view(self):
        try:
            self.env.cr.execute("""
                REFRESH MATERIALIZED VIEW CONCURRENTLY bi_sales_summary_mv;
                REFRESH MATERIALIZED VIEW CONCURRENTLY bi_daily_user_location_summary_mv;
            """)
            _logger.info("Materialized Views refreshed successfully.")
            return {'status': 'success', 'message': 'Materialized Views refreshed'}
        except Exception as e:
            _logger.error(f"Failed to refresh Materialized Views: {str(e)}")
            return {'status': 'error', 'message': str(e)}


class BiSalesSummaryMV(models.Model):
    _name = 'bi.sales.summary.mv'
    _description = 'BI Sales Summary Materialized View'
    _auto = False

    id = fields.Integer('ID', readonly=True)
    x_vendor_name = fields.Char('Vendor')
    x_sales_team = fields.Char('Sales Team')
    x_product_name = fields.Char('Product')
    x_parent_product_name = fields.Char('Parent Product')
    x_product_categ = fields.Char('Product Category')
    x_order_date = fields.Date('Order Date')
    x_pos_qty = fields.Float('POS Qty')
    x_pos_sales = fields.Float('POS Sales')
    x_credit_qty = fields.Float('Credit Qty')
    x_credit_sales = fields.Float('Credit Sales')
    x_total_qty = fields.Float('Total Qty')
    x_total_sales = fields.Float('Total Sales')
    x_cost_price = fields.Float('Cost Price')
    x_total_cost = fields.Float('Total Cost')
    x_profit = fields.Float('Profit')
    x_margin_percentage = fields.Float('Margin %')

    def init(self):
        self._cr.execute("""
            SELECT 1 FROM pg_matviews WHERE matviewname = 'bi_sales_summary_mv';
        """)
        if not self._cr.fetchone():
            _logger.warning("Materialized view bi_sales_summary_mv not found. Please create it.")


class BiDailyUserLocationSummary(models.Model):
    _name = 'bi.daily.user.location.summary.mv'
    _description = 'Daily Sales, Purchases, and Expenses by User Location'
    _auto = False

    id = fields.Integer('ID', readonly=True)
    user_working_location = fields.Char(string="Working Location")
    order_date = fields.Date(string="Date")
    total_sales = fields.Float(string="Total Sales")
    total_purchase = fields.Float(string="Total Purchase")
    total_expense = fields.Float(string="Total Expense")

    def init(self):
        self._cr.execute("""
            SELECT 1 FROM pg_matviews WHERE matviewname = 'bi_daily_user_location_summary_mv';
        """)
        if not self._cr.fetchone():
            _logger.warning("Materialized view bi_daily_user_location_summary_mv not found. Please create it.")
