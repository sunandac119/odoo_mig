import odoo.addons.decimal_precision as dp
from odoo import models, fields, api, _
from odoo.addons.sale_stock.models.sale_order import SaleOrderLine
from odoo.exceptions import Warning, ValidationError, UserError


class sale_order(models.Model):
    _inherit = 'sale.order'

    def action_confirm(self):
        res = super(sale_order, self).action_confirm()
        for order in self:
            if order.pricelist_id:
                for lines in order.order_line.filtered(lambda l: l.price_unit > 0.00):
                    pricelist_item = order.pricelist_id.item_ids.filtered(lambda
                                                                              l: l.compute_price == 'fixed' and l.applied_on == '1_product' and l.uom_id.id == lines.product_uom.id)
                    if pricelist_item:
                        each_price = order.pricelist_id.item_ids.search(
                            [('product_tmpl_id', '=', lines.product_id.product_tmpl_id.id),
                             ('compute_price', '=', 'fixed'), ('applied_on', '=', '1_product'),
                             ('pricelist_id', '=', order.pricelist_id.id), ('uom_id', '=', lines.product_uom.id)])
                        if not each_price:
                            order.pricelist_id.write({'item_ids': [(0, 0, {'applied_on': '1_product',
                                                                           'product_tmpl_id': lines.product_id.product_tmpl_id.id,
                                                                           'uom_id': lines.product_uom.id,
                                                                           'fixed_price': lines.price_unit})]})
                        else:
                            each_price.fixed_price = lines.price_unit
                    else:
                        order.pricelist_id.write({'item_ids': [(0, 0, {'applied_on': '1_product',
                                                                       'product_tmpl_id': lines.product_id.product_tmpl_id.id,
                                                                       'uom_id': lines.product_uom.id,
                                                                       'fixed_price': lines.price_unit
                                                                       })]})
        return res


class SaleOrderLineInherit(models.Model):
    _inherit = "sale.order.line"

    @api.onchange('product_id')
    def product_id_change(self):
        for order in self:
            if not order.product_id:
                return {'domain': {'product_uom': []}}

            vals = {}
            domain = {'product_uom': [('category_id', '=', order.product_id.uom_id.category_id.id)]}
            if not order.product_uom or (order.product_id.uom_id.id != order.product_uom.id):
                vals['product_uom'] = order.product_id.uom_id
                vals['product_uom_qty'] = 1.0

            product = order.product_id.with_context(
                lang=order.order_id.partner_id.lang,
                partner=order.order_id.partner_id.id,
                quantity=vals.get('product_uom_qty') or order.product_uom_qty,
                date=order.order_id.date_order,
                pricelist=order.order_id.pricelist_id.id,
                uom=order.product_uom.id
            )

            result = {'domain': domain}

            title = False
            message = False
            warning = {}
            if product.sale_line_warn != 'no-message':
                title = _("Warning for %s") % product.name
                message = product.sale_line_warn_msg
                warning['title'] = title
                warning['message'] = message
                result = {'warning': warning}
                if product.sale_line_warn == 'block':
                    order.product_id = False
                    return result

            name = product.name_get()[0][1]
            if product.description_sale:
                name += '\n' + product.description_sale
            vals['name'] = name

            order._compute_tax_id()

            if order.order_id.pricelist_id and order.order_id.partner_id:
                vals['price_unit'] = self.env['account.tax']._fix_tax_included_price_company(
                    order._get_display_price(product), product.taxes_id, order.tax_id, order.company_id)
            order.update(vals)

        return result

    def check_get_price(self, uom=False, product=False):
        if product:
            price = product.list_price
        else:
            price = 0.0

        if self.order_id.pricelist_id:
            if uom:
                if product:
                    if len(self.order_id.pricelist_id.item_ids) > 0:
                        for item in self.order_id.pricelist_id.item_ids:
                            if item.compute_price == 'fixed':
                                if uom.id == item.uom_id.id and item.min_quantity >= self.product_uom_qty:
                                    if item.applied_on == '2_product_category' \
                                            and product.product_tmpl_id.categ_id.id == item.categ_id.id:
                                        return item.fixed_price
                                    elif item.applied_on == '1_product' and (
                                            product.product_tmpl_id.id == item.product_tmpl_id.id):
                                        self.write({
                                            'product_uom': item.uom_id.id
                                        })
                                        return item.fixed_price
                                    elif item.applied_on == '0_product_variant' and (
                                            product.product_tmpl_id.id == item.product_tmpl_id.id):
                                        return item.fixed_price
                                    elif item.applied_on == '3_global':
                                        return item.fixed_price
                            else:
                                return product.with_context(pricelist=self.order_id.pricelist_id.id,
                                                            uom=self.product_uom.id).price
                    else:
                        return product.with_context(pricelist=self.order_id.pricelist_id.id,
                                                    uom=self.product_uom.id).price
        return price

    def _get_display_price(self, product):
        # TO DO: move me in master/saas-16 on sale.order
        # awa: don't know if it's still the case since we need the "product_no_variant_attribute_value_ids" field now
        # to be able to compute the full price

        # it is possible that a no_variant attribute is still in a variant if
        # the type of the attribute has been changed after creation.
        no_variant_attributes_price_extra = [
            ptav.price_extra for ptav in self.product_no_variant_attribute_value_ids.filtered(
                lambda ptav:
                ptav.price_extra and
                ptav not in product.product_template_attribute_value_ids
            )
        ]
        if no_variant_attributes_price_extra:
            product = product.with_context(
                no_variant_attributes_price_extra=tuple(no_variant_attributes_price_extra)
            )
        if self.order_id.pricelist_id.discount_policy == 'with_discount':
            self.check_get_price(self.product_uom, self.product_id)
        product_context = dict(self.env.context, partner_id=self.order_id.partner_id.id, date=self.order_id.date_order,
                               uom=self.product_uom.id)

        final_price, rule_id = self.order_id.pricelist_id.with_context(product_context).get_product_price_rule(
            product or self.product_id, self.product_uom_qty or 1.0, self.order_id.partner_id)
        base_price, currency = self.with_context(product_context)._get_real_price_currency(product, rule_id,
                                                                                           self.product_uom_qty,
                                                                                           self.product_uom,
                                                                                           self.order_id.pricelist_id.id)

        if currency != self.order_id.pricelist_id.currency_id:
            base_price = currency._convert(
                base_price, self.order_id.pricelist_id.currency_id,
                self.order_id.company_id or self.env.company, self.order_id.date_order or fields.Date.today())
        # negative discounts (= surcharge) are included in the display price
        return max(base_price, final_price)

    @api.onchange('product_uom', 'product_uom_qty')
    def product_uom_change(self):
        if not self.product_uom or not self.product_id:
            self.price_unit = 0.0
            return
        if self.order_id.pricelist_id and self.order_id.partner_id:
            product = self.product_id.with_context(
                lang=self.order_id.partner_id.lang,
                partner=self.order_id.partner_id,
                quantity=self.product_uom_qty,
                date=self.order_id.date_order,
                pricelist=self.order_id.pricelist_id.id,
                uom=self.product_uom.id,
                fiscal_position=self.env.context.get('fiscal_position')
            )
            self.price_unit = product._get_tax_included_unit_price(
                self.company_id or self.order_id.company_id,
                self.order_id.currency_id,
                self.order_id.date_order,
                'sale',
                fiscal_position=self.order_id.fiscal_position_id,
                product_price_unit=self._get_display_price(product),
                product_currency=self.order_id.currency_id
            )

            self.price_unit = self.check_get_price(self.product_uom, self.product_id)
