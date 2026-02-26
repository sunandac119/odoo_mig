from odoo import fields, models, tools

class LowSalesReport(models.Model):
    _name = 'low.sales.report.pivot'
    _auto = False
    _description = 'Low Sales Report'
    _rec_name = 'product_id'

    product_id = fields.Many2one('product.product', string='Product', readonly=True)
    total_qty_sold = fields.Float(string='Total Quantity Sold (Unit)', readonly=True)
    ctn_qty_sold = fields.Float(string='Total Quantity Sold (Carton)', readonly=True)
    total_revenue = fields.Float('Total Revenue', readonly=True)
    unit_price = fields.Float('Average Unit Price', readonly=True)

    def _select_sale(self, fields=None):
        if not fields:
            fields = {}
        select_ = """
            min(l.id) as id,
            l.product_id as product_id,
            SUM(l.product_uom_qty) as total_qty_sold,
            CASE WHEN t.ctn_unit > 0 THEN SUM(l.product_uom_qty) / t.ctn_unit ELSE 0 END as ctn_qty_sold,
            AVG(l.price_unit) as unit_price,
            SUM(l.product_uom_qty * l.price_unit) as total_revenue
        """
        for field in fields.values():
            select_ += field
        return select_

    def _from_sale(self, from_clause=''):
        from_ = """
            sale_order_line l
            LEFT JOIN sale_order s ON (s.id = l.order_id)
            LEFT JOIN product_product p ON (l.product_id = p.id)
            LEFT JOIN product_template t ON (p.product_tmpl_id = t.id)
            %s
        """ % from_clause
        return from_

    def _group_by_sale(self, groupby=''):
        groupby_ = """
            l.product_id,
            t.ctn_unit
            %s
        """ % (groupby)
        return groupby_

    def _select_additional_fields(self, fields):
        return fields

    def _query(self, with_clause='', fields=None, groupby='', from_clause=''):
        if not fields:
            fields = {}
        sale_report_fields = self._select_additional_fields(fields)
        with_ = ("WITH %s" % with_clause) if with_clause else ""
        return '%s (SELECT %s FROM %s WHERE l.display_type IS NULL GROUP BY %s)' % (
            with_,
            self._select_sale(sale_report_fields),
            self._from_sale(from_clause),
            self._group_by_sale(groupby)
        )

    def init(self):
        tools.drop_view_if_exists(self.env.cr, self._table)
        self.env.cr.execute("""CREATE or REPLACE VIEW %s AS (%s)""" % (self._table, self._query()))
