# -*- coding: utf-8 -*-
# Powered by Kanak Infosystems LLP.
# © 2020 Kanak Infosystems LLP. (<https://www.kanakinfosystems.com>).
from odoo import api, fields, models


class SaleOrderLine(models.Model):
    _inherit = 'sale.order.line'

    analytic_account_id = fields.Many2one('account.analytic.account', string="Analytic Account", related="order_id.analytic_account_id")
    packaging_price = fields.Float(string="Packaging Price", compute="_compute_packaging_price", default="0.0")
    product_packaging_qty = fields.Float('Packaging Quantity')

    @api.depends('price_unit', 'product_packaging')
    def _compute_packaging_price(self):
        for rec in self:
            if rec.product_packaging:
                rec.packaging_price = rec.product_packaging.qty * rec.price_unit
            else:
                rec.packaging_price = 0.0

    @api.onchange('product_id')
    def product_id_change(self):
        res = super(SaleOrderLine, self).product_id_change()
        for rec in self:
            if rec.product_id:
                packaging = self.env['product.packaging'].search([('product_id', '=', rec.product_id.id), ('default', '=', True)], limit=1)
                rec.product_uom_qty = packaging.qty
        return res

    @api.depends('product_uom_qty', 'discount', 'price_unit', 'tax_id')
    def _compute_amount(self):
        """
        Compute the amounts of the SO line.
        """
        for line in self:
            price = line.price_unit * (1 - (line.discount or 0.0) / 100.0)
            if line.product_packaging and line.product_packaging_qty:
                taxes = line.tax_id.compute_all(price, line.order_id.currency_id, line.product_packaging_qty, product=line.product_id, partner=line.order_id.partner_shipping_id)
            else:
                taxes = line.tax_id.compute_all(price, line.order_id.currency_id, line.product_uom_qty, product=line.product_id, partner=line.order_id.partner_shipping_id)
            line.update({
                'price_tax': taxes['total_included'] - taxes['total_excluded'],
                'price_total': taxes['total_included'],
                'price_subtotal': taxes['total_excluded'],
            })
            if self.env.context.get('import_file', False) and not self.env.user.user_has_groups('account.group_account_manager'):
                line.tax_id.invalidate_cache(['invoice_repartition_line_ids'], [line.tax_id.id])

    def _prepare_invoice_line(self, **optional_values):
        res = super(SaleOrderLine, self)._prepare_invoice_line()
        res['product_packaging_id'] = self.product_packaging
        res['product_packaging_qty'] = self.qty_delivered
        return res


class SaleOrder(models.Model):
    _inherit = "sale.order"

    customer_sign = fields.Binary(string="Signature")
    analytic_account_id = fields.Many2one('account.analytic.account', string="Analytic Account")
    analytic_tag_ids = fields.Many2many('account.analytic.tag', string="Analytic Account Tags")
    vehicle_journey_id = fields.Many2one('vehicle.journey', string="Vehicle Journey")

    def load_order_form(self):
        orders = self.search([('partner_id', '=', self.partner_id.id), ('state', 'in', ['done', 'sale'])], limit=10)
        if orders:
            query = """SELECT product_id, product_packaging, product_packaging_qty, product_uom_qty FROM sale_order_line WHERE order_id IN %(orders)s"""
            self.env.cr.execute(query, {'orders': tuple(orders.ids)})
            result = self.env.cr.fetchall()
            vals = []
            products = self.order_line.mapped('product_id')
            for x in range(0, len(result)):
                if result[x][0] not in products.ids:
                    vals.append((0, 0, {'product_id': result[x][0], 'product_packaging': result[x][1], 'product_packaging_qty': result[x][2], 'product_uom_qty': result[x][2]}))
            self.order_line = vals
        return


class PivotInheritReport(models.Model):
    _inherit = 'sale.report'

    product_packaging = fields.Many2one('product.packaging')

    def _query(self, with_clause='', fields={}, groupby='', from_clause=''):
        fields['product_packaging'] = ", l.product_packaging as product_packaging"
        return super(PivotInheritReport, self)._query(with_clause, fields, groupby, from_clause)

    def _group_by_sale(self, groupby=''):
        return super(PivotInheritReport, self)._group_by_sale() + ", l.product_packaging"

    def _from_sale(self, from_clause=''):
        res = super(PivotInheritReport, self)._from_sale()
        res += """
            left join product_packaging pc on (pc.id=l.product_packaging)
        """
        return res
