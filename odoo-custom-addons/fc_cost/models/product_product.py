from odoo import models, api

class ProductProduct(models.Model):
    _inherit = 'product.product'

    @api.model
    def recalculate_variant_cost(self, product_variant_id):
        # Query to find all relevant stock moves linked to the product variant
        query = """
            WITH filtered_moves AS (
                SELECT 
                    sm.id AS stock_move_id,
                    sm.product_qty AS receive_qty,
                    sm.price_unit AS receive_cost,
                    pt.unit_qty AS unit_qty,
                    (sm.price_unit * sm.product_qty) AS total_cost,
                    (sm.product_qty * COALESCE(pt.unit_qty, 1)) AS adjusted_qty,
                    pp.id AS product_variant_id
                FROM 
                    stock_move sm
                INNER JOIN 
                    product_product pp ON sm.product_id = pp.id
                INNER JOIN 
                    product_template pt ON pp.product_tmpl_id = pt.id
                WHERE 
                    pp.id = %s -- Specific product variant ID
                    AND sm.state = 'done' -- Only completed stock moves
                    AND sm.picking_type_id IN (
                        SELECT id FROM stock_picking_type WHERE code = 'incoming'
                    ) -- Only incoming moves
            )
            SELECT
                fm.product_variant_id,
                SUM(fm.total_cost) AS total_cost,
                SUM(fm.adjusted_qty) AS total_adjusted_qty,
                COALESCE(MAX(fm.unit_qty), 1) AS unit_qty,
                CASE
                    WHEN SUM(fm.total_cost) = 0 THEN 0
                    ELSE (SUM(fm.total_cost) / NULLIF(SUM(fm.adjusted_qty), 0)) * COALESCE(MAX(fm.unit_qty), 1)
                END AS recalculated_unit_cost
            FROM 
                filtered_moves fm
            GROUP BY 
                fm.product_variant_id;
        """
        self.env.cr.execute(query, (product_variant_id,))
        result = self.env.cr.dictfetchone()

        if result and result['recalculated_unit_cost'] is not None:
            # Update the standard_price if recalculated cost differs
            product_variant = self.browse(product_variant_id)
            if product_variant.standard_price != result['recalculated_unit_cost']:
                product_variant.sudo().write({'standard_price': result['recalculated_unit_cost']})
                return f"Unit cost updated for product_variant_id {product_variant_id}: {result['recalculated_unit_cost']}"

        return f"No update needed for product_variant_id {product_variant_id}"
