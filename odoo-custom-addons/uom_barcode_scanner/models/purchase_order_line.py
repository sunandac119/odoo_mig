# -*- coding: utf-8 -*-
from odoo import models, fields, api
from odoo.tools.misc import get_lang
from dateutil.relativedelta import relativedelta
import math
import logging

_logger = logging.getLogger(__name__)


class PurchaseOrder(models.Model):
    _inherit = "purchase.order"

    vendor_display = fields.Char(string="Vendor Display", compute="_compute_vendor_display", store=False)
    po_picking_count = fields.Integer(string="Picking")
    po_invoice_count = fields.Integer(string="Vendor Bills")

    def action_view_po_invoice(self):
        self.ensure_one()
        return {
            "name": "Invoices",
            "type": "ir.actions.act_window",
            "res_model": "account.move",
            "view_mode": "tree,form",
            "domain": [
                ("invoice_origin", "=", self.name),
                ("move_type", "in", ["in_invoice", "in_refund"]),
            ],
            "context": {"default_invoice_origin": self.name, "default_move_type": "in_invoice"},
        }

    def action_view_po_picking(self):
        self.ensure_one()
        return {
            "name": "Pickings",
            "type": "ir.actions.act_window",
            "res_model": "stock.picking",
            "view_mode": "tree,form",
            "domain": [("origin", "=", self.name)],
            "context": {"default_origin": self.name},
        }

    def button_confirm(self):
        # skip supplier auto-add (your existing logic)
        res = super(PurchaseOrder, self.with_context(skip_add_supplier=True)).button_confirm()

        # push barcode + description + uom to stock moves/move lines
        for order in self:
            for line in order.order_line:
                barcode = line.x_scanned_barcode
                uom = line.product_uom

                if uom and (uom.name or "").strip().lower() != "unit":
                    description = f"{line.product_id.display_name} X {uom.name}"
                else:
                    description = line.product_id.display_name

                stock_moves = self.env["stock.move"].search([("purchase_line_id", "=", line.id)])
                for move in stock_moves:
                    move.write({
                        "x_scanned_barcode": barcode,
                        "description_picking": description,
                        "product_uom_qty": line.product_qty,
                        "product_uom": uom.id,
                    })
                    for ml in move.move_line_ids:
                        ml.write({
                            "x_scanned_barcode": barcode,
                            "description": description,
                            "product_uom_qty": line.product_qty,
                            "product_uom_id": uom.id,
                        })

        return res

    def _add_supplier_to_product(self):
        if self.env.context.get("skip_add_supplier"):
            return
        return super(PurchaseOrder, self)._add_supplier_to_product()

    @api.depends("partner_id", "partner_id.x_studio_account_code", "partner_id.name")
    def _compute_vendor_display(self):
        for order in self:
            if order.partner_id:
                code = order.partner_id.x_studio_account_code or ""
                name = order.partner_id.display_name or ""
                order.vendor_display = f"{code} - {name}" if code else name
            else:
                order.vendor_display = ""


class PurchaseOrderLine(models.Model):
    _inherit = "purchase.order.line"

    x_scanned_barcode = fields.Char(string="Barcode")
    rounding = fields.Float(string="Rounding")
    _barcode_uom_id = fields.Many2one("uom.uom", string="Barcode UOM", store=False)

    # NEW: track manual unit price edit (so we don’t override user price)
    is_manual_price = fields.Boolean(string="Manual Price", default=False)

    # ------------------------------------------------------------
    # PRICE ENGINE (always converts seller price -> current UOM)
    # ------------------------------------------------------------
    def _get_seller_price_date(self):
        """Return (price_unit, date_planned) converted to current product_uom."""
        self.ensure_one()

        if not self.product_id or not self.order_id:
            return 0.0, self.order_id.date_planned

        vendor = self.order_id.partner_id
        sellers = self.product_id.seller_ids.filtered(lambda s: s.name == vendor)
        if not sellers:
            sellers = self.product_id.seller_ids[:1]
        if not sellers:
            return 0.0, self.order_id.date_planned

        seller = sellers[0]

        date_order = self.order_id.date_order or fields.Date.today()

        def _get_date_planned(s):
            dt = date_order + relativedelta(days=s.delay or 0)
            return self._convert_to_middle_of_day(dt)

        seller_uom = seller.product_uom or self.product_id.uom_po_id or self.product_id.uom_id
        target_uom = self.product_uom or self.product_id.uom_po_id or self.product_id.uom_id

        # if category mismatch, cannot convert safely
        if seller_uom.category_id != target_uom.category_id:
            _logger.warning(
                "UOM category mismatch: seller_uom=%s target_uom=%s product=%s",
                seller_uom.name, target_uom.name, self.product_id.display_name
            )
            price = seller.price or 0.0
        else:
            # 🔥 Always convert from seller_uom to target_uom
            price = seller_uom._compute_price(seller.price or 0.0, target_uom)

        return price, _get_date_planned(seller)

    def _recompute_price_if_allowed(self):
        """Recompute price if user did not manually edit unit price."""
        self.ensure_one()
        if self.is_manual_price:
            return
        price, date_planned = self._get_seller_price_date()
        self.price_unit = price
        if date_planned:
            self.date_planned = date_planned

    # ------------------------------------------------------------
    # ONCHANGE: barcode scan -> set product + uom -> recalc price
    # ------------------------------------------------------------
    @api.onchange("x_scanned_barcode")
    def _onchange_x_scanned_barcode(self):
        if not self.x_scanned_barcode:
            self._barcode_uom_id = False
            return

        BarcodeUom = self.env["product.barcode.uom"]
        barcode_line = BarcodeUom.search([("barcode", "=", self.x_scanned_barcode)], limit=1)

        if barcode_line:
            product = barcode_line.product_id.product_variant_id
            if not product:
                self._barcode_uom_id = False
                return

            self.is_manual_price = False  # scanning should reapply vendor price
            self.product_id = product.id
            self._barcode_uom_id = barcode_line.uom_id.id
            self.product_uom = barcode_line.uom_id.id
            self.name = barcode_line.description or product.name

            self._recompute_price_if_allowed()

        else:
            # fallback to product search by default_code or barcode
            product = self.env["product.product"].search(
                [("default_code", "=", self.x_scanned_barcode)], limit=1
            )
            if not product:
                product = self.env["product.product"].search(
                    [("barcode", "=", self.x_scanned_barcode)], limit=1
                )

            if product:
                self.is_manual_price = False
                self.product_id = product.id
                self.product_uom = product.uom_po_id.id or product.uom_id.id
                self._recompute_price_if_allowed()
            else:
                self.price_unit = 0.0

        # Set domain for allowed UOMs (your custom relation)
        if self.product_id:
            allowed_uoms = self.product_id.barcode_uom_ids.mapped("uom_id").ids
            if allowed_uoms:
                return {"domain": {"product_uom": [("id", "in", allowed_uoms)]}}

    # ------------------------------------------------------------
    # ONCHANGE: user changes UOM -> recalc price (convert)
    # ------------------------------------------------------------
    @api.onchange("product_uom")
    def _onchange_product_uom_recalc_price(self):
        # user changed UOM, we should convert vendor price again (unless manual price)
        self._recompute_price_if_allowed()

        # sync scanned barcode to selected uom (your custom model)
        if self.product_id and self.product_uom:
            uom_line = self.env["product.barcode.uom"].search([
                ("product_id", "=", self.product_id.product_tmpl_id.id),
                ("uom_id", "=", self.product_uom.id),
            ], limit=1)
            if uom_line:
                self.x_scanned_barcode = uom_line.barcode

    # ------------------------------------------------------------
    # ONCHANGE: user edits price manually -> lock price
    # ------------------------------------------------------------
    @api.onchange("price_unit")
    def _onchange_price_unit_mark_manual(self):
        # mark manual ONLY when user typed (not when system sets)
        if not self.env.context.get("skip_manual_price_flag"):
            # if we already have a product, treat as manual
            if self.product_id:
                self.is_manual_price = True

    # ------------------------------------------------------------
    # PRODUCT CHANGE (keep your override but add price recompute)
    # ------------------------------------------------------------
    def _product_id_change(self):
        if not self.product_id:
            return

        self.product_uom = (
            self._barcode_uom_id.id
            if self.x_scanned_barcode and self._barcode_uom_id
            else (self.product_id.uom_po_id or self.product_id.uom_id)
        )

        product_lang = self.product_id.with_context(
            lang=get_lang(self.env, self.partner_id.lang).code,
            partner_id=self.partner_id.id,
            company_id=self.company_id.id,
        )
        self.name = self._get_product_purchase_description(product_lang)
        self._compute_tax_id()

        # set vendor price (unless manual)
        self._recompute_price_if_allowed()

    # ------------------------------------------------------------
    # WRITE: if uom/product changed server-side, recompute price
    # ------------------------------------------------------------
    def write(self, vals):
        if self.env.context.get("skip_vendor_update"):
            return super(PurchaseOrderLine, self).write(vals)

        res = super(PurchaseOrderLine, self).write(vals)

        # Recompute if product/uom changed and price not manually locked
        if any(k in vals for k in ("product_id", "product_uom")):
            for line in self:
                if line.is_manual_price:
                    continue
                price, date_planned = line._get_seller_price_date()
                super(PurchaseOrderLine, line.with_context(skip_vendor_update=True)).write({
                    "price_unit": price,
                    "date_planned": date_planned,
                })

        return res

    # ------------------------------------------------------------
    # AMOUNT / ROUNDING (keep yours)
    # ------------------------------------------------------------
    @api.depends("product_qty", "price_unit", "taxes_id", "rounding")
    def _compute_amount(self):
        for line in self:
            if "UNIT" not in (line.product_uom.name or "").upper():
                line.name = f"{line.product_id.name} X {line.product_uom.name}"
            else:
                line.name = line.product_id.name

            vals = line._prepare_compute_all_values()
            taxes = line.taxes_id.compute_all(
                vals["price_unit"],
                vals["currency_id"],
                vals["product_qty"],
                vals["product"],
                vals["partner"],
            )

            raw_subtotal = taxes["total_excluded"]
            adjusted_subtotal = raw_subtotal
            r = line.rounding or 0.0

            if r:
                if 0.0 <= r <= 0.2:
                    adjusted_subtotal = math.floor(raw_subtotal)
                elif 0.3 <= r <= 0.4 or 0.6 <= r <= 0.7:
                    adjusted_subtotal = math.floor(raw_subtotal) + 0.5
                elif 0.8 <= r <= 0.99:
                    adjusted_subtotal = math.ceil(raw_subtotal)

            tax_amt = sum(t.get("amount", 0.0) for t in taxes.get("taxes", []))

            line.update({
                "price_tax": tax_amt,
                "price_total": adjusted_subtotal + tax_amt,
                "price_subtotal": adjusted_subtotal,
            })

    # ------------------------------------------------------------
    # PRODUCT DESCRIPTION (keep yours)
    # ------------------------------------------------------------
    def _get_product_purchase_description(self, product_lang):
        self.ensure_one()
        if self._barcode_uom_id and self.x_scanned_barcode:
            barcode_line = self.env["product.barcode.uom"].search(
                [("barcode", "=", self.x_scanned_barcode)], limit=1
            )
            if barcode_line and barcode_line.description:
                return barcode_line.description

            if barcode_line:
                if "UNIT" not in (self.product_uom.name or "").upper():
                    return f"{product_lang.name} X {barcode_line.uom_id.name}"
                return product_lang.name

        return super()._get_product_purchase_description(product_lang)
