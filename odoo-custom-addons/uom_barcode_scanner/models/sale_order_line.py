from odoo import models, fields, api
from datetime import datetime, date
import logging, re
from odoo.exceptions import ValidationError
from odoo.tools import float_compare

_logger = logging.getLogger(__name__)


class SaleOrderLine(models.Model):
    _inherit = 'sale.order.line'

    x_scanned_barcode = fields.Char(string="Barcode")
    _barcode_price_override = fields.Float(string="Barcode Price Override", store=False)
    _skip_pricelist_computation = fields.Boolean(string="Skip Pricelist", store=False, default=False)
    x_manual_discount = fields.Boolean('Manual Discount', default=False)

    # @api.constrains('product_uom_qty')
    # def _check_product_uom_qty(self):
    #     for line in self:
    #         if line.product_uom_qty <= 0:
    #             raise ValidationError("The quantity must be greater than 0.")

    # ---------------------- ONCHANGE BARCODE ----------------------


    @api.onchange('discount')
    def _onchange_discount(self):
        # When user edits discount in the form, mark it manual (client-side)
        for rec in self:
            # Only mark if change looks manual (this onchange runs when user edits)
            rec.x_manual_discount = True

    @api.model
    def create(self, vals):
        # If discount is provided in vals and not a programmatic update, mark manual
        if 'discount' in vals and not self.env.context.get('barcode_auto_update'):
            vals = dict(vals)
            vals['x_manual_discount'] = True
        return super().create(vals)

    def write(self, vals):
        # If discount provided by client and not a programmatic update, mark manual
        if 'discount' in vals and not self.env.context.get('barcode_auto_update'):
            vals = dict(vals)
            vals['x_manual_discount'] = True
            _logger.debug("Marking x_manual_discount for sale.order.line ids %s", self.ids)
        return super().write(vals)

    def reset_manual_discount(self):
        """Helper to revert to automatic behaviour (call from UI or server action)."""
        return self.write({'x_manual_discount': False})

    @api.onchange('x_scanned_barcode')
    def _onchange_x_scanned_barcode(self):
        barcode = (self.x_scanned_barcode or "").strip()
        if not barcode:
            self._barcode_price_override = 0.0
            self._skip_pricelist_computation = False
            return

        _logger.info(f"=== PROCESSING BARCODE: {barcode} ===")

        barcode_line = self.env['product.barcode.uom'].search([('barcode', '=', barcode)], limit=1)

        if barcode_line:
            _logger.info(f"=== FOUND BARCODE LINE: {barcode_line.product_id.name} / {barcode_line.uom_id.name} ===")

            product = self.env['product.product'].search(
                [('product_tmpl_id', '=', barcode_line.product_id.id)], limit=1
            )
            if product:
                barcode_price = barcode_line.sale_price or product.lst_price or 0.0
                pricelist_price = self._get_price_from_pricelist_or_barcode(product, barcode_line)

                self._barcode_price_override = barcode_price
                self._skip_pricelist_computation = True
                self.product_id = product.id
                self.product_uom = barcode_line.uom_id.id
                self.product_uom_qty = 0.0
                self.price_unit = barcode_price
                self.name = (
                    barcode_line.description
                    or (f"{product.name} X {barcode_line.uom_id.name}" if "UNIT" not in (self.product_uom.name or "").upper() else product.name)
                )
                # Adjust subtotal using discount
                if pricelist_price and barcode_price:
                    self.discount = max(0.0, (1 - (pricelist_price / barcode_price)) * 100)
                else:
                    self.discount = 0.0

                _logger.info(f"=== SET: Product={product.name}, UOM={barcode_line.uom_id.name}, "
                             f"BarcodePrice={barcode_price}, PricelistPrice={pricelist_price}, "
                             f"Discount={self.discount} ===")

            else:
                _logger.error("=== NO PRODUCT VARIANT FOUND ===")

        elif len(barcode) <= 5:  # Internal reference match
            _logger.info("=== TRYING INTERNAL REFERENCE SEARCH ===")
            product = self.env['product.product'].search([('default_code', '=', barcode)], limit=1)
            if product:
                self.product_id, self.product_uom, self.price_unit = product.id, product.uom_id.id, product.lst_price
                self.product_uom_qty = 0.0
            else:
                _logger.warning("=== NO PRODUCT FOUND FOR INTERNAL REFERENCE ===")

        else:
            _logger.info("=== NO MULTI-UOM BARCODE FOUND ===")
            self._barcode_price_override = 0.0
            self._skip_pricelist_computation = False

        if self.product_id:
            allowed_uoms = self.product_id.barcode_uom_ids.mapped('uom_id').ids
            return {'domain': {'product_uom': [('id', 'in', allowed_uoms)]}}

    # ---------------------- ONCHANGE UOM ----------------------
    @api.onchange('product_uom', 'product_uom_qty')
    def onchange_uom(self):
        if not self.product_id:
            return

        # --- Update name with UoM ---
        # self.name = (
        #     f"{self.product_id.name} X {self.product_uom.name}"
        #     if self.product_uom and "UNIT" not in (self.product_uom.name or "").upper()
        #     else self.product_id.name
        # )

        qty = self.product_uom_qty or 1.0
        barcode_line = self.env['product.barcode.uom'].search([
            ('product_id', '=', self.product_id.product_tmpl_id.id),
            ('uom_id', '=', self.product_uom.id)
        ], limit=1)

        if barcode_line:
            self.x_scanned_barcode = barcode_line.barcode

            if barcode_line and barcode_line.sale_price > 0:
                # Always set price_unit = barcode sale price
                self.price_unit = barcode_line.sale_price
                self.discount = 0.0

                pricelist = self.order_id.pricelist_id if self.order_id else False
                if pricelist:
                    product_ctx = self.product_id.with_context(uom=self.product_uom.id)
                    pricelist_ctx = pricelist.with_context(uom=self.product_uom.id)

                    pricelist_price, rule_id = pricelist_ctx.get_product_price_rule(
                        product_ctx, qty, self.order_id.partner_id
                    )

                    if pricelist_price > 0:
                        # Apply difference as discount, not by changing unit price
                        self.discount = max(0.0, (1 - (pricelist_price / barcode_line.sale_price)) * 100)
                        _logger.info(
                            f"=== ONCHANGE UOM: price_unit={self.price_unit}, "
                            f"pricelist_price={pricelist_price}, discount={self.discount} ==="
                        )


    # ---------------------- ONCHANGE PRODUCT ----------------------
    @api.onchange('product_id')
    def product_id_change(self):
        """Keep normal product onchange, but prevent it from overwriting name/uom if barcode scan happened"""
        if self.x_scanned_barcode and self._barcode_price_override > 0 and self._skip_pricelist_computation:
            _logger.info("=== BARCODE SCAN: skipping full onchange ===")
            if self.product_id and not self.name:
                self.name = self.product_id.display_name
            if self.product_id and not self.product_uom:
                self.product_uom = self.product_id.uom_id.id
            return
        return super().product_id_change()

    def _get_display_price(self, product):
        """Force display unit price to always be barcode sale price."""
        if self.x_scanned_barcode:
            barcode_line = self.env['product.barcode.uom'].search([
                ('product_id', '=', product.product_tmpl_id.id),
                ('uom_id', '=', self.product_uom.id)
            ], limit=1)
            if barcode_line and barcode_line.sale_price > 0:
                return barcode_line.sale_price
        return super()._get_display_price(product)


    def _compute_amount(self):
        """Always keep price_unit as barcode sale_price, apply pricelist as discount."""
        super(SaleOrderLine, self)._compute_amount()
        for line in self:
            if line.x_scanned_barcode:
                barcode_line = self.env['product.barcode.uom'].search([
                    ('product_id', '=', line.product_id.product_tmpl_id.id),
                    ('uom_id', '=', line.product_uom.id)
                ], limit=1)

                if barcode_line and barcode_line.sale_price > 0:
                    # Force unit price = barcode sale price
                    line.price_unit = barcode_line.sale_price

                    pricelist = line.order_id.pricelist_id
                    pricelist_price = 0.0
                    if pricelist:
                        product_ctx = line.product_id.with_context(uom=line.product_uom.id)
                        pricelist_ctx = pricelist.with_context(uom=line.product_uom.id)
                        pricelist_price, _ = pricelist_ctx.get_product_price_rule(
                            product_ctx, line.product_uom_qty, line.order_id.partner_id
                        )

                    if not line.x_manual_discount:
                        if pricelist_price > 0:
                            computed_discount = max(0.0, (1 - (pricelist_price / barcode_line.sale_price)) * 100)
                        else:
                            computed_discount = 0.0

                        # write discount only if it differs (prevents recursion)
                        if float_compare(line.discount or 0.0, computed_discount or 0.0, precision_digits=2) != 0:
                            line.with_context(barcode_auto_update=True).write({'discount': computed_discount})

                    # Now recompute subtotal/taxes
                    taxes = line.tax_id.compute_all(
                        line.price_unit * (1 - line.discount / 100.0),
                        currency=line.order_id.currency_id,
                        quantity=line.product_uom_qty,
                        product=line.product_id,
                        partner=line.order_id.partner_id,
                    )
                    line.update({
                        'price_tax': sum(t.get('amount', 0.0) for t in taxes['taxes']),
                        'price_total': taxes['total_included'],
                        'price_subtotal': taxes['total_excluded'],
                    })


    # ---------------------- ONCHANGE PRODUCT OVERRIDE ----------------------
    @api.onchange('product_id', 'product_uom_qty', 'product_uom', 'pricelist_id')
    def _onchange_product_override(self):
        barcode, override_price, skip_pricelist = (
            self.x_scanned_barcode, self._barcode_price_override, self._skip_pricelist_computation
        )
        _logger.info(f"=== PRODUCT OVERRIDE ONCHANGE ===\nBarcode: {barcode}\nOverride price: {override_price}\nSkip pricelist: {skip_pricelist}")

        barcode_line = self.env['product.barcode.uom'].search([('barcode', '=', barcode)], limit=1)

        if barcode and override_price > 0 and skip_pricelist and barcode_line and self.product_id:
            _logger.info("=== MAINTAINING BARCODE VALUES ===")
            if not self.name:
                self.name = self.product_id.display_name
            if barcode_line.sale_price and override_price > barcode_line.sale_price:
                raise ValidationError(
                    f"Pricelist price ({override_price}) is higher than original product price "
                    f"({barcode_line.sale_price}) for product '{self.name}'."
                )
            self.product_uom, self.price_unit = barcode_line.uom_id.id, override_price
            _logger.info(f"=== MAINTAINED: UOM={barcode_line.uom_id.name}, Price={override_price} ===")
            return

        if self.env.context.get('skip_uom_logic'):
            return

        # if self.product_id and self.product_uom_qty:
        #     qty, all_uoms = int(self.product_uom_qty), self.product_id.barcode_uom_ids.mapped('uom_id')
        #     match_found = False

            # for uom in all_uoms:
            #     match = re.search(r'\d+', uom.name or "")
            #     if match and int(match.group(0)) == qty:
            #         _logger.info(f"=== MATCH FOUND: QTY={qty}, UOM={uom.name} ===")
            #         self.product_uom = uom.id
            #         self = self.with_context(skip_uom_logic=True)
            #         self.product_uom_qty, match_found = 1, True
            #         break

            # if not match_found and barcode_line and qty != 1:
            #     _logger.info(f"=== NO MATCH, FALLBACK TO BARCODE UOM: {barcode_line.uom_id.name} ===")
            #     self.product_uom = barcode_line.uom_id.id

    # ---------------------- PRICE CALCULATION ----------------------
    def _get_price_from_pricelist_or_barcode(self, product, barcode_line):
        pricelist, partner, uom_id, qty = (
            self.order_id.pricelist_id, self.order_id.partner_id, barcode_line.uom_id, self.product_uom_qty or 1.0
        )
        current_date = (self.order_id.date_order.date() if self.order_id.date_order else date.today())

        _logger.info(f"=== CALCULATING PRICE ===\nPricelist: {pricelist.name if pricelist else 'None'}\nUOM: {uom_id.name}\nQuantity: {qty}\nCurrent Date: {current_date}")

        if pricelist:
            items = self.env['product.pricelist.item'].search([
                ('pricelist_id', '=', pricelist.id),
                ('product_tmpl_id', '=', product.product_tmpl_id.id),
                ('product_id', 'in', [False, product.id]),
                '|', ('uom_id', '=', False), ('uom_id', '=', uom_id.id)
            ])
            valid_items = [i for i in items if self._is_pricelist_item_valid_for_date(i, current_date)]
            _logger.info(f"Valid pricelist items found: {len(valid_items)}")

            if valid_items:
                item = valid_items[0]
                if item.compute_price == 'fixed' and item.fixed_price > 0:
                    return item.fixed_price

        return (
            barcode_line.sale_price if barcode_line.sale_price and barcode_line.sale_price > 0
            else product.lst_price or 0.0
        )

    # ---------------------- PRICELIST DATE CHECK ----------------------
    def _is_pricelist_item_valid_for_date(self, item, check_date):
        if isinstance(check_date, datetime):
            check_date = check_date.date()
        start, end = item.date_start, item.date_end
        start, end = (start.date() if isinstance(start, datetime) else start), (end.date() if isinstance(end, datetime) else end)

        if not start and not end: return True
        if start and not end: return check_date >= start
        if not start and end: return check_date <= end
        if start and end: return start <= check_date <= end
        return False



class SaleOrder(models.Model):
    _inherit = 'sale.order'

    so_invoice_count = fields.Integer(string='Invoices')
    validate_picking = fields.Boolean('Validate picking')

    def action_view_so_invoice(self):
        """Open related invoices for the sale order"""
        self.ensure_one()
        return {
            'name': 'Invoices',
            'type': 'ir.actions.act_window',
            'res_model': 'account.move',
            'view_mode': 'tree,form',
            'domain': [
                ('invoice_origin', '=', self.name),
                ('move_type', 'in', ['out_invoice', 'out_refund']),
            ],
            'context': {'default_invoice_origin': self.name, 'default_move_type': 'out_invoice'},
        }

    def action_confirm(self):
        res = super(SaleOrder, self).action_confirm()
        for order in self:
            for line in order.order_line:
                barcode = line.x_scanned_barcode
                uom = line.product_uom

                # Dynamic description
                if uom and uom.name.lower() != "unit":
                    description = f"{line.product_id.display_name} X {uom.name}"
                else:
                    description = line.product_id.display_name

                stock_moves = self.env['stock.move'].search([
                    ('sale_line_id', '=', line.id)
                ])

                for move in stock_moves:
                    move.write({
                        'x_scanned_barcode': barcode,
                        'description_picking': description,
                        'product_uom_qty': line.product_uom_qty,
                        'product_uom': uom.id,
                    })

                    for move_line in move.move_line_ids:
                        move_line.write({
                            'x_scanned_barcode': barcode,
                            'description': description,
                            'product_uom_qty': line.product_uom_qty,
                            'product_uom_id': uom.id,
                        })

        return res


