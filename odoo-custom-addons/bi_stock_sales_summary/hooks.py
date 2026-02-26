def create_materialized_views(cr):
    cr.execute("""
        DROP MATERIALIZED VIEW IF EXISTS bi_sales_summary_mv;
        CREATE MATERIALIZED VIEW bi_sales_summary_mv AS
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

        DROP MATERIALIZED VIEW IF EXISTS bi_ordering_report_mv;
        CREATE MATERIALIZED VIEW bi_ordering_report_mv AS
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
