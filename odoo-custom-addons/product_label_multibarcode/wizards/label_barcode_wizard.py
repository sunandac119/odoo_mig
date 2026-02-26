# -*- coding: utf-8 -*-
from odoo import api, fields, models
from odoo.exceptions import UserError
import logging
_logger = logging.getLogger(__name__)



class LabelBarcodeWizard(models.TransientModel):
    _name = "label.barcode.wizard"
    _description = "Label Barcode Wizard"

    line_ids = fields.One2many(
        "label.barcode.wizard.line", "wizard_id", string="Label Lines", copy=False
    )

    barcode_type = fields.Selection(
        selection=[
            ("EAN13", "EAN-13"),
            ("EAN8", "EAN-8"),
            ("UPCA", "UPC-A"),
            ("Code128", "Code-128"),
            ("Code39", "Code-39"),
            ("QR", "QR"),
        ],
        default="Code128",
        required=True,
    )
    include_humanreadable = fields.Boolean(
        string="Show human-readable text", default=True
    )
    label_cols = fields.Integer(string="Columns per row", default=3)

    print_layout_id = fields.Many2one('ir.actions.report', domain = "[('model','=','product.product')]")

    # V2 quick UoM filter
    desired_uom_id = fields.Many2one("uom.uom", string="Filter by UoM")

    @api.model
    def default_get(self, fields_list):
        res = super().default_get(fields_list)
        active_model = self.env.context.get("active_model")
        active_ids = self.env.context.get("active_ids", [])
        lines = []

        if active_model in ("product.product", "product.template") and active_ids:
            if active_model == "product.product":
                products = self.env["product.product"].browse(active_ids)
            else:
                templates = self.env["product.template"].browse(active_ids)
                products = templates.mapped("product_variant_id")

            for product in products:
                # 1) Primary barcode (if any)
                if product.barcode:
                    lines.append(
                        (0, 0, {
                            "product_id": product.id,
                            "product_tmpl_id": product.product_tmpl_id.id,
                            "uom_id": product.product_tmpl_id.uom_id.id,
                            "barcode": product.barcode,
                            "qty": 1,
                            "select": True,
                        })
                    )

                # 2) Extra multi-UoM barcodes (from your custom module)
                for mb in self._iter_multi_barcodes(product):
                    if mb.get("barcode"):
                        lines.append(
                            (0, 0, {
                                "product_id": product.id,
                                "product_tmpl_id": product.product_tmpl_id.id,
                                "uom_id": mb.get("uom_id"),
                                "barcode": mb.get("barcode"),
                                "qty": 0,
                                "select": False,
                            })
                        )

        res["line_ids"] = lines
        return res

    # --- Helpers -----------------------------------------------------------
    def _iter_multi_barcodes(self, product):
        """
        Yield dicts {barcode: str, uom_id: int} from known models.
        Adjust this to match your multi-barcode schema.
        Tries a few common patterns; skip silently if a model is missing.
        """
        tmpl = product.product_tmpl_id
        env = self.env

        # Pattern A: pos.multi_uom_barcode (example fields)
        try:
            Model = env["pos.multi_uom_barcode"]
        except KeyError:
            Model = None
        if Model:
            try:
                recs = Model.search([("product_tmpl_id", "=", tmpl.id)])
                for r in recs:
                    if getattr(r, "barcode", False):
                        yield {"barcode": r.barcode, "uom_id": r.uom_id.id if r.uom_id else False}
            except Exception:
                pass

        # Pattern B: product.barcode.uom (example fields)
        try:
            Model = env["product.barcode.uom"]
        except KeyError:
            Model = None
        if Model:
            try:
                recs = Model.search([("product_tmpl_id", "=", tmpl.id)])
                for r in recs:
                    if getattr(r, "barcode", False):
                        yield {"barcode": r.barcode, "uom_id": r.uom_id.id if r.uom_id else False}
            except Exception:
                pass

        # Pattern C: product.multi.barcode linked to product
        try:
            Model = env["product.multi.barcode"]
        except KeyError:
            Model = None
        if Model:
            try:
                recs = Model.search([("product_id", "in", product.ids)])
                for r in recs:
                    if getattr(r, "barcode", False):
                        uom = getattr(r, "uom_id", False)
                        yield {"barcode": r.barcode, "uom_id": uom.id if uom else False}
            except Exception:
                pass

    # --- Quick actions -----------------------------------------------------
    def action_select_by_uom(self):
        self.ensure_one()
        for l in self.line_ids:
            l.select = (not self.desired_uom_id) or (l.uom_id and l.uom_id.id == self.desired_uom_id.id)
        return True

    def action_unselect_all(self):
        self.ensure_one()
        self.line_ids.write({"select": False})
        return True

    # --- Print -------------------------------------------------------------
    def action_print(self):
        self.ensure_one()

        selected_lines = self.line_ids.filtered(lambda l: l.select)

        if not selected_lines:
            raise UserError("No templates selected to print.")

        products = self.env['product.product']

        for line in selected_lines:
            if not line.barcode:
                continue

            product = self.env['product.product'].search([('barcode', '=', line.barcode),('active', 'in', [True, False])], limit=1)

            if not product:
                product = self.env['product.product'].search([('barcode_uom_ids.barcode', '=', line.barcode)], limit=1)

            if product:
                products |= product

        if not products:
            raise UserError("No products found for the selected barcodes.")

        if self.print_layout_id.report_name == "product_label_multibarcode.report_product_label":
            return {
                "type": "ir.actions.act_window",
                "res_model": "print.product.label",
                "view_mode": "form",
                "target": "new",
                "context": {
                    "default_product_ids": products.ids,
                    "wizard_active_model": 'product.product',
                },
            }

        return self.print_layout_id.report_action(products)
        

class LabelBarcodeWizardLine(models.TransientModel):
    _name = "label.barcode.wizard.line"
    _description = "Label Barcode Wizard Line"

    wizard_id = fields.Many2one(
        "label.barcode.wizard", required=True, ondelete="cascade"
    )
    product_id = fields.Many2one("product.product", string="Product Variant")
    product_tmpl_id = fields.Many2one("product.template", string="Product Template")
    uom_id = fields.Many2one(
        "uom.uom",
        string="UoM",
        domain=lambda self: self._get_uom_domain()
    )
    barcode = fields.Char(string="Barcode", required=True)
    qty = fields.Integer(string="Labels", default=1)
    select = fields.Boolean(string="Print?", default=True)

    display_name = fields.Char(
        string="Label Title", compute="_compute_display_name", store=False
    )

    @api.onchange('barcode')
    def _onchange_barcode(self):
        if not self.barcode:
            return

        barcode_line = self.env['product.barcode.uom'].search([
            ('barcode', '=', self.barcode)
        ], limit=1)

        if barcode_line:
            self.product_tmpl_id = barcode_line.product_id.id
            product = self.env['product.product'].search([
                ('product_tmpl_id', '=', barcode_line.product_id.id)
            ], limit=1)

            if product:
                self.product_id = product.id
                self.uom_id = barcode_line.uom_id.id

        elif len(self.barcode.strip()) <= 5:
            _logger.info("=== TRYING INTERNAL REFERENCE SEARCH ===")
            product = self.env['product.product'].search([
                ('default_code', '=', self.barcode)
            ], limit=1)
            if product:
                self.product_tmpl_id = product.product_tmpl_id.id
                self.uom_id = product.uom_id.id
            else:
                _logger.warning("=== NO PRODUCT FOUND FOR INTERNAL REFERENCE ===")

        if self.product_tmpl_id:
            allowed_uoms = self.product_tmpl_id.barcode_uom_ids.mapped('uom_id').ids
            return {'domain': {'uom_id': [('id', 'in', allowed_uoms)]}}

    @api.onchange('uom_id')
    def _onchange_uom_id(self):
        for rec in self:
            if rec.product_tmpl_id and rec.uom_id:
                barcode_line = rec.product_tmpl_id.barcode_uom_ids.filtered(
                    lambda b: b.uom_id == rec.uom_id
                )
                if barcode_line:
                    rec.barcode = barcode_line[0].barcode
                    rec.display_name = barcode_line[0].description

    @api.depends("product_id", "product_tmpl_id", "uom_id")
    def _compute_display_name(self):
        for rec in self:
            parts = []
            name = rec.product_id.display_name or rec.product_tmpl_id.display_name
            if name:
                parts.append(name)
            if rec.uom_id:
                parts.append("[{}]".format(rec.uom_id.name))
            rec.display_name = " ".join(parts) or rec.barcode or "Label"

    def _get_uom_domain(self):
        if self and self.product_tmpl_id:
            allowed_uoms = self.product_tmpl_id.barcode_uom_ids.mapped('uom_id').ids
            return [('id', 'in', allowed_uoms)]
        return []
