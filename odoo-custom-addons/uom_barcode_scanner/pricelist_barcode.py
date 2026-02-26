from odoo import models, fields, api, _, tools
import logging
from itertools import chain
from odoo.exceptions import UserError, ValidationError
from datetime import datetime
import pytz

_logger = logging.getLogger(__name__)


class ProductPricelistItem(models.Model):
    _inherit = 'product.pricelist.item'

    x_scanned_barcode = fields.Char(string="Barcode")
    uom_id = fields.Many2one('uom.uom', 'Pricelist UOM')

    _sql_constraints = [
        ('check_uom_id', 'CHECK(uom_id IS NOT NULL)', _('Please select a Price list UOM.')),
    ]

    x_studio_cost = fields.Float(
        string="Cost",
        compute="_compute_barcode_prices",
        store=True
    )
    x_studio_related_field_ebwDn = fields.Float(
        string="Related Price",
        compute="_compute_barcode_prices",
        store=True
    )

    @api.depends('x_scanned_barcode', 'product_tmpl_id', 'uom_id')
    def _compute_barcode_prices(self):
        for rec in self:
            rec.x_studio_cost = 0.0
            rec.x_studio_related_field_ebwDn = 0.0
            if rec.x_scanned_barcode:
                barcode_line = self.env['product.barcode.uom'].search([
                    ('barcode', '=', rec.x_scanned_barcode)
                ], limit=1)
                if barcode_line and barcode_line.sale_price:
                    rec.x_studio_cost = barcode_line.sale_price
                    rec.x_studio_related_field_ebwDn = barcode_line.sale_price


    @api.onchange('date_end')
    def _onchange_date_end(self):
        for rec in self:
            if rec.date_end:
                _logger.info("=== Onchange Triggered for record ID: %s ===", rec.id)
                _logger.info("Original date_end (UTC naive): %s", rec.date_end)

                user_tz = self.env.user.tz or 'UTC'
                _logger.info("User Timezone: %s", user_tz)

                tz = pytz.timezone(user_tz)
                dt_utc = fields.Datetime.from_string(rec.date_end)
                _logger.info("Datetime converted from string (UTC): %s", dt_utc)

                dt_user = dt_utc.replace(tzinfo=pytz.UTC).astimezone(tz)
                _logger.info("Datetime in user timezone: %s", dt_user)

                now_user = fields.Datetime.context_timestamp(self, datetime.utcnow())
                _logger.info("Current datetime in user timezone: %s", now_user)

                _logger.info(
                    "Comparing hours/minutes: (%s, %s) vs (%s, %s)",
                    dt_user.hour, dt_user.minute, now_user.hour, now_user.minute
                )

                if (dt_user.hour, dt_user.minute) == (now_user.hour, now_user.minute):
                    _logger.info("Time matches current hour/minute → adjusting to 23:59:59")
                    dt_user = dt_user.replace(hour=23, minute=59, second=59)
                    dt_utc = dt_user.astimezone(pytz.UTC)
                    rec.date_end = dt_utc.replace(tzinfo=None)
                    _logger.info("Updated date_end (back to UTC naive): %s", rec.date_end)
                else:
                    _logger.info("No change made to date_end")

                _logger.info("=== End of Onchange ===")


    @api.onchange('uom_id')
    def onchange_uom(self):
        self.applied_on = '1_product'
        barcode_line = self.env['product.barcode.uom'].search([
            ('product_id', '=', self.product_id.product_tmpl_id.id),
            ('uom_id', '=', self.uom_id.id)
        ], limit=1)

        if barcode_line:
            self.x_scanned_barcode = barcode_line.barcode

    @api.onchange('product_tmpl_id')
    def _onchange_product_tmpl_id(self):
        if self.product_tmpl_id:
            # Update the domain for uom_id based on the selected product template
            return {'domain': {'uom_id': [('category_id', '=', self.product_tmpl_id.uom_id.category_id.id)]}}


    @api.onchange('x_scanned_barcode')
    def _onchange_x_scanned_barcode(self):
        self.applied_on = '1_product'
        if not self.x_scanned_barcode:
            return

        # Search directly in product.barcode.uom
        barcode_line = self.env['product.barcode.uom'].search([
            ('barcode', '=', self.x_scanned_barcode)
        ], limit=1)

        if barcode_line:
            self.applied_on = '1_product'
            self.product_tmpl_id = barcode_line.product_id.id
            self.uom_id = barcode_line.uom_id.id
            product = self.env['product.product'].search([
                ('product_tmpl_id', '=', barcode_line.product_id.id)
            ], limit=1)

            if product:
                self.product_id = product.id

            # Set the Pricelist UOM from barcode line - field name is uom_id as per your second image
            # if barcode_line.uom_id:
            #     # Based on your second image, the field name is uom_id for Pricelist UOM
            #     if hasattr(self, 'uom_id'):
            #         self.uom_id = barcode_line.uom_id.id
            #     else:
            #         # Fallback for different field names
            #         for field_name in ['pricelist_uom_id', 'product_uom', 'base_pricelist_uom']:
            #             if hasattr(self, field_name):
            #                 setattr(self, field_name, barcode_line.uom_id.id)
            #                 break

            # Set price from barcode line
            if barcode_line.sale_price:
                self.fixed_price = barcode_line.sale_price

        else:
            # If no barcode line found, try standard product barcode
            products = self.env['product.product'].search([('barcode', '=', self.x_scanned_barcode)])
            if products:
                product = products[0]
                self.applied_on = '1_product'
                self.product_tmpl_id = product.product_tmpl_id.id
                self.product_id = product.id
                # Set default UOM
                if hasattr(self, 'uom_id'):
                    self.uom_id = product.uom_id.id

        if self.product_id:
            # Get allowed UoM IDs from product's barcode_uom_ids
            allowed_uoms = self.product_id.barcode_uom_ids.mapped('uom_id').ids
            return {
                'domain': {
                    'uom_id': [
                        ('id', 'in', allowed_uoms)
                    ]
                }
            }
    
    def _compute_price(self, price, price_uom, product, quantity=1.0, partner=False):

        """Compute the unit price of a product in the context of a pricelist application.
           The unused parameters are there to make the full context available for overrides.
        """
        self.ensure_one()
        convert_to_price_uom = (lambda price: product.uom_id._compute_price(price, price_uom))
        if self.compute_price == 'fixed':
            price = self.fixed_price
        elif self.compute_price == 'percentage':
            price = (price - (price * (self.percent_price / 100))) or 0.0
        else:
            # complete formula
            price_limit = price
            price = (price - (price * (self.price_discount / 100))) or 0.0

            if self.price_round:
                price = tools.float_round(price, precision_rounding=self.price_round)

            if self.price_surcharge:
                price += convert_to_price_uom(self.price_surcharge)

            if self.price_min_margin:
                price_min_margin = convert_to_price_uom(self.price_min_margin)
                price = max(price, price_limit + price_min_margin)

            if self.price_max_margin:
                price_max_margin = convert_to_price_uom(self.price_max_margin)
                price = min(price, price_limit + price_max_margin)
        return price

class ProductPricelist(models.Model):
    _inherit = 'product.pricelist'

    @api.model
    def create(self, vals):
        pricelist_name = vals.get("name")

        # Get scanned barcode from vals
        item_vals = vals.get("item_ids", [])
        if item_vals and item_vals[0][2].get("x_scanned_barcode"):
            barcode = item_vals[0][2]["x_scanned_barcode"]

            # Find barcode line
            barcode_line = self.env["product.barcode.uom"].search([
                ("barcode", "=", barcode)
            ], limit=1)

            if barcode_line:
                item_vals[0][2]["uom_id"] = barcode_line.uom_id.id

        if pricelist_name:
            existing_pricelist = self.env["product.pricelist"].search(
                [("name", "=", pricelist_name)], limit=1
            )
            if existing_pricelist:
                # Add item to existing pricelist instead of creating new
                existing_pricelist.write({
                    "item_ids": [(0, 0, item_vals[0][2])]
                })
                return existing_pricelist

        # Default behavior if pricelist doesn't exist
        return super().create(vals)

    def _compute_price_rule(self, products_qty_partner, date=False, uom_id=False):
        """ Low-level method - Mono pricelist, multi products
        Returns: dict{product_id: (price, suitable_rule) for the given pricelist}

        Date in context can be a date, datetime, ...

            :param products_qty_partner: list of typles products, quantity, partner
            :param datetime date: validity date
            :param ID uom_id: intermediate unit of measure
        """
        self.ensure_one()
        if not date:
            date = self._context.get('date') or fields.Datetime.now()
        if not uom_id and self._context.get('uom'):
            uom_id = self._context['uom']

        if uom_id:
            # rebrowse with uom if given
            products = [item[0].with_context(uom=uom_id) for item in products_qty_partner]
            products_qty_partner = [(products[index], data_struct[1], data_struct[2]) for index, data_struct in enumerate(products_qty_partner)]
        else:
            products = [item[0] for item in products_qty_partner]

        if not products:
            return {}

        categ_ids = {}
        for p in products:
            categ = p.categ_id
            while categ:
                categ_ids[categ.id] = True
                categ = categ.parent_id
        categ_ids = list(categ_ids)

        is_product_template = products[0]._name == "product.template"
        if is_product_template:
            prod_tmpl_ids = [tmpl.id for tmpl in products]
            # all variants of all products
            prod_ids = [p.id for p in
                        list(chain.from_iterable([t.product_variant_ids for t in products]))]
        else:
            prod_ids = [product.id for product in products]
            prod_tmpl_ids = [product.product_tmpl_id.id for product in products]

        items = self._compute_price_rule_get_items(products_qty_partner, date, uom_id, prod_tmpl_ids, prod_ids, categ_ids)

        results = {}
        for product, qty, partner in products_qty_partner:
            results[product.id] = 0.0
            suitable_rule = False

            # Final unit price is computed according to `qty` in the `qty_uom_id` UoM.
            # An intermediary unit price may be computed according to a different UoM, in
            # which case the price_uom_id contains that UoM.
            # The final price will be converted to match `qty_uom_id`.

            qty_uom_id = self._context.get('uom') or product.uom_id.id
            qty_in_product_uom = qty
            # if qty_uom_id != product.uom_id.id:
            #     try:
            #         qty_in_product_uom = self.env['uom.uom'].browse([self._context['uom']])._compute_quantity(qty, product.uom_id)
            #     except UserError:
            #         # Ignored - incompatible UoM in context, use default product UoM
            #         pass

            # if Public user try to access standard price from website sale, need to call price_compute.
            # TDE SURPRISE: product can actually be a template
            price = product.price_compute('list_price')[product.id]
            price_uom = self.env['uom.uom'].browse([qty_uom_id])
            for rule in items:
                if rule.min_quantity and qty_in_product_uom < rule.min_quantity:
                    continue
                if is_product_template:
                    if rule.product_tmpl_id and product.id != rule.product_tmpl_id.id:
                        continue
                    if rule.product_id and not (product.product_variant_count == 1 and product.product_variant_id.id == rule.product_id.id):
                        # product rule acceptable on template if has only one variant
                        continue
                else:
                    if rule.product_tmpl_id and product.product_tmpl_id.id != rule.product_tmpl_id.id:
                        continue
                    if rule.product_id and product.id != rule.product_id.id:
                        continue

                if rule.categ_id:
                    cat = product.categ_id
                    while cat:
                        if cat.id == rule.categ_id.id:
                            break
                        cat = cat.parent_id
                    if not cat:
                        continue

                if rule.uom_id:
                    if rule.uom_id.id != price_uom.id:
                        continue

                if rule.base == 'pricelist' and rule.base_pricelist_id:
                    price = rule.base_pricelist_id._compute_price_rule([(product, qty, partner)], date, uom_id)[product.id][0]  # TDE: 0 = price, 1 = rule
                    src_currency = rule.base_pricelist_id.currency_id
                else:
                    # if base option is public price take sale price else cost price of product
                    # price_compute returns the price in the context UoM, i.e. qty_uom_id
                    price = product.price_compute(rule.base)[product.id]
                    if rule.base == 'standard_price':
                        src_currency = product.cost_currency_id
                    else:
                        src_currency = product.currency_id

                if src_currency != self.currency_id:
                    price = src_currency._convert(
                        price, self.currency_id, self.env.company, date, round=False)

                if price is not False:
                    barcode_line = self.env['product.barcode.uom'].search([
                        ('product_id', '=', product.product_tmpl_id.id),
                        ('uom_id', '=', price_uom.id)
                    ], limit=1)
                    if barcode_line and barcode_line.sale_price:
                        # Use the price from barcode line if available
                        price = barcode_line.sale_price
                    price = rule._compute_price(price, price_uom, product, quantity=qty, partner=partner)
                    suitable_rule = rule

                break

            if not suitable_rule:
                    
                barcode_line = self.env['product.barcode.uom'].search([
                    ('product_id', '=', product.product_tmpl_id.id),
                    ('uom_id', '=', price_uom.id)
                ], limit=1)
                if barcode_line and barcode_line.sale_price:
                    # Use the price from barcode line if available
                    price = barcode_line.sale_price
                    results[product.id] = (price, suitable_rule and suitable_rule.id or False)
                    return results
                cur = product.currency_id
                price = cur._convert(price, self.currency_id, self.env.company, date, round=False)
                
            results[product.id] = (price, suitable_rule and suitable_rule.id or False)
        return results
