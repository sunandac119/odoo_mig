from odoo import models, fields, api
from datetime import datetime, date
import logging, re
from odoo.exceptions import ValidationError
from odoo.tools import float_compare

_logger = logging.getLogger(__name__)


class AccountMoveLine(models.Model):
    _inherit = 'account.move.line'

    x_scanned_barcode = fields.Char(string="Barcode")
    _barcode_price_override = fields.Float(string="Barcode Price Override", store=False)
    _skip_pricelist_computation = fields.Boolean(string="Skip Pricelist", store=False, default=False)

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
                self._barcode_price_override = barcode_price
                self._skip_pricelist_computation = True
                self.product_id = product.id
                self.product_uom_id = barcode_line.uom_id.id
                # self.product_uom_qty = 0.0
                self.price_unit = barcode_price
                self.name = (
                    barcode_line.description
                    or (f"{product.name} X {barcode_line.uom_id.name}" if "UNIT" not in (self.product_uom.name or "").upper() else product.name)
                )
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


    @api.onchange('amount_currency')
    def _onchange_amount_currency(self):
        super(AccountMoveLine, self)._onchange_amount_currency()

        for line in self:
            if getattr(line, "_skip_pricelist_computation", False) and getattr(line, "_barcode_price_override", 0):
                line.price_unit = line._barcode_price_override
                line.update(line._get_price_total_and_subtotal())
            