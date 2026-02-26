from odoo import models, fields, api
import logging, re
from odoo.exceptions import ValidationError

_logger = logging.getLogger(__name__)


class SaleReturnLine(models.Model):
    _inherit = 'sale.return.line'


    x_scanned_barcode = fields.Char(string="Barcode")
    is_barcode_price_set = fields.Boolean(string="Is Barcode Price Set", default=False)
    name = fields.Char(string="Description")

    # @api.constrains('qty_return')
    # def _check_product_uom_qty(self):
    #     for line in self:
    #         if line.qty_return <= 0:
    #             raise ValidationError("The quantity must be greater than 0.")

    # ---------------------- ONCHANGE PRODUCT/QTY ----------------------
    @api.onchange('product_id', 'qty_return')
    def get_unit_uom(self):
        if not self.product_id:
            return

        # Only set default UoM if not already set (avoid overriding barcode UoM)
        if not self.product_uom:
            self.product_uom = self.product_id.uom_id.id

        # Keep price from barcode if already set, else fallback to product price
        if not self.is_barcode_price_set:
            self.price_unit = self.product_id.lst_price

        # Skip further logic if flagged
        # if self.env.context.get('skip_uom_logic') or not self.qty_return:
        #     return

        qty_entered = int(self.qty_return)
        # match_found = False

        # If barcode was scanned, fetch its line
        barcode_line = None
        if self.x_scanned_barcode:
            barcode_line = self.env['product.barcode.uom'].search([
                ('barcode', '=', self.x_scanned_barcode)
            ], limit=1)

        # for uom in self.product_id.barcode_uom_ids.mapped('uom_id'):
        #     match = re.search(r'\d+', uom.name or "")
        #     if match and int(match.group(0)) == qty_entered:
        #         _logger.info(f"=== MATCH FOUND: QTY={qty_entered}, UOM={uom.name} ===")
        #         self.product_uom = uom.id
        #         self = self.with_context(skip_uom_logic=True)
        #         self.qty_return, match_found = 1, True
        #         break

        # Optional fallback (kept disabled as in your code)
        # if not match_found and barcode_line and qty_entered != 1:
        #     self.product_uom = barcode_line.uom_id.id


    # ---------------------- ONCHANGE UOM ----------------------
    @api.onchange('product_uom', 'qty_return')
    def onchange_uom(self):
        if self.product_id and self.product_uom:
            # Always recompute price based on selected UoM
            uom_line = self.env['product.barcode.uom'].search([
                ('product_id', '=', self.product_id.product_tmpl_id.id),
                ('uom_id', '=', self.product_uom.id)
            ], limit=1)

            if uom_line:
                self.x_scanned_barcode = uom_line.barcode

                if uom_line and uom_line.sale_price:
                    self.price_unit = uom_line.sale_price
                    _logger.info(f"=== UNIT PRICE UPDATED ON UOM CHANGE: {uom_line.sale_price} for UOM={self.product_uom.name} ===")
                else:
                    # fallback to conversion from product's base UoM price
                    self.price_unit = self.product_id.uom_id._compute_price(
                        self.product_id.list_price, self.product_uom
                    )
                    _logger.info(f"=== UNIT PRICE FALLBACK (converted): {self.price_unit} ===")
        if self.product_id:
            self.name = (
                f"{self.product_id.name} X {self.product_uom.name}"
                if self.product_uom and "UNIT" not in (self.product_uom.name or "").upper()
                else self.product_id.name
            )

    # ---------------------- ONCHANGE BARCODE ----------------------
    @api.onchange('x_scanned_barcode')
    def _onchange_x_scanned_barcode(self):
        self.is_barcode_price_set = False
        barcode = (self.x_scanned_barcode or "").strip()
        if not barcode:
            return

        barcode_line = self.env['product.barcode.uom'].search([('barcode', '=', barcode)], limit=1)
        product = None

        if barcode_line:
            product = self.env['product.product'].search(
                [('product_tmpl_id', '=', barcode_line.product_id.id)], limit=1
            )
            if product:
                self.is_barcode_price_set = True
                self.product_id, self.product_uom = product.id, barcode_line.uom_id.id
                self.price_unit = barcode_line.sale_price
                self.product_qty = 0.0

        elif len(barcode) <= 5:  # Internal reference match
            _logger.info("=== TRYING INTERNAL REFERENCE SEARCH ===")
            product = self.env['product.product'].search([('default_code', '=', barcode)], limit=1)
            if product:
                self.product_id, self.product_uom, self.price_unit = product.id, product.uom_id.id, product.lst_price
            else:
                _logger.warning("=== NO PRODUCT FOUND FOR INTERNAL REFERENCE ===")

        else:  # Standard product barcode
            product = self.env['product.product'].search([('barcode', '=', barcode)], limit=1)
            if product:
                self.is_barcode_price_set = True
                self.product_id, self.product_uom, self.price_unit = product.id, product.uom_id.id, product.lst_price
                self.product_qty = 0.0

        if product:
            self.name = (
                (barcode_line.description or f"{product.name} X {barcode_line.uom_id.name}")
                if barcode_line and "UNIT" not in (self.product_uom.name or "").upper()
                else (barcode_line.description or product.name)
            )

            allowed_uoms = product.barcode_uom_ids.mapped('uom_id').ids
            return {'domain': {'product_uom': [('id', 'in', allowed_uoms)]}}

    # ---------------------- ONCHANGE UOM ----------------------
    # @api.onchange('product_uom', 'qty_return')
    # def onchange_uom(self):
    #     if not self.product_id or not self.product_uom:
    #         return

    #     # === Update description ===
    #     product_name = self.product_id.name or ''
    #     uom_name = self.product_uom.name or ''
    #     self.name = f"{product_name} X {uom_name}" if "UNIT" not in uom_name.upper() else product_name

    #     # === Update price when UOM is changed ===
    #     barcode_line = self.env['product.barcode.uom'].search([
    #         ('product_id', '=', self.product_id.product_tmpl_id.id),
    #         ('uom_id', '=', self.product_uom.id)
    #     ], limit=1)

    #     if barcode_line and barcode_line.sale_price:
    #         self.price_unit = barcode_line.sale_price
    #         self.is_barcode_price_set = True
    #         _logger.info(f"=== PRICE UPDATED FROM BARCODE UOM: {barcode_line.sale_price} ({self.product_uom.name}) ===")
    #     else:
    #         # fallback to product list price
    #         self.price_unit = self.product_id.lst_price
    #         self.is_barcode_price_set = False
    #         _logger.info(f"=== PRICE FALLBACK TO DEFAULT: {self.price_unit} ({self.product_uom.name}) ===")



class SaleReturn(models.Model):
    _inherit = 'sale.return'


    def action_process(self):
        if self.order_line_ids:
            returns = self.order_line_ids.filtered(lambda r: r.qty_return > 0)
            if returns:
                self.create_picking_returns(returns)
            else:
                raise ValidationError(_("No line to return picking"))
            self.state = 'done'

            # ---------------- Extra logic: update stock moves and move lines ----------------
            for order in self:
                for line in order.order_line_ids:
                    barcode = getattr(line, "x_scanned_barcode", False)
                    uom = line.product_uom

                    # Dynamic description
                    if uom and uom.name.lower() != "unit":
                        description = f"{line.product_id.display_name} X {uom.name}"
                    else:
                        description = line.product_id.display_name

                    stock_moves = self.env['stock.move'].search([
                        ('sale_return_line_id', '=', line.id)
                    ])

                    for move in stock_moves:
                        move.write({
                            'x_scanned_barcode': barcode,
                            'name': description,
                            'description_picking': description,
                            'product_uom_qty': line.qty_return,
                            'product_uom': uom.id,
                        })

                        for move_line in move.move_line_ids:
                            move_line.write({
                                'x_scanned_barcode': barcode,
                                'description': description,
                                'qty_done': line.qty_return,
                                'product_uom_id': uom.id,
                            })

        else:
            raise ValidationError(_("No lines"))
