from odoo import models, fields, api

class StockWarehouseOrderpoint(models.Model):
    _inherit = 'stock.warehouse.orderpoint'

    @api.model
    def update_orderpoint_quantity(self):
        # Query to fetch the sum of on hand quantities multiplied by unit_qty, grouped by parent_product_template_id and warehouse
        self.env.cr.execute("""
            SELECT
                pt.parent_product_template_id,
                sw.id as warehouse_id,
                SUM(quant.quantity * pt.unit_qty) as total_qty
            FROM
                stock_quant quant
            JOIN
                product_product pp ON quant.product_id = pp.id
            JOIN
                product_template pt ON pp.product_tmpl_id = pt.id
            JOIN
                stock_location loc ON quant.location_id = loc.id
            JOIN
                stock_warehouse sw ON loc.warehouse_id = sw.id
            WHERE
                loc.usage = 'internal'
            GROUP BY
                pt.parent_product_template_id, sw.id
        """)
        results = self.env.cr.fetchall()

        # Iterate over the result and update the stock.warehouse.orderpoint
        for parent_product_template_id, warehouse_id, total_qty in results:
            # Search for existing orderpoint for this parent product template and warehouse
            orderpoint = self.env['stock.warehouse.orderpoint'].search([
                ('product_id.product_tmpl_id.parent_product_template_id', '=', parent_product_template_id),
                ('warehouse_id', '=', warehouse_id)
            ], limit=1)

            if orderpoint:
                orderpoint.write({
                    'product_min_qty': total_qty  # Update the product_min_qty field with total_qty
                })
            else:
                # Optionally, create a new orderpoint record if it doesn't exist
                product_id = self.env['product.product'].search([
                    ('product_tmpl_id.parent_product_template_id', '=', parent_product_template_id)
                ], limit=1).id
                if product_id:
                    self.env['stock.warehouse.orderpoint'].create({
                        'product_id': product_id,
                        'warehouse_id': warehouse_id,
                        'product_min_qty': total_qty
                    })
