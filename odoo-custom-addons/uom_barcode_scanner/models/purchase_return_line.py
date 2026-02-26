from odoo import models, fields, api, _
import logging
import re
from odoo.exceptions import ValidationError

_logger = logging.getLogger(__name__)


class PurchaseReturn(models.Model):
    _inherit = 'purchase.return'

    vendor_display = fields.Char(
        string="Vendor Display",
        compute="_compute_vendor_display",
        store=False
    )

    @api.depends('partner_id', 'partner_id.x_studio_account_code', 'partner_id.name')
    def _compute_vendor_display(self):
        for order in self:
            if order.partner_id:
                code = order.partner_id.x_studio_account_code or ''
                name = order.partner_id.display_name or ''
                order.vendor_display = f"{code} - {name}" if code else name
            else:
                order.vendor_display = ''

    def action_process(self):
        _logger = logging.getLogger(__name__)
        _logger.info("Calling PurchaseReturn.action_process()")

        if not self.order_line_ids:
            raise ValidationError(_("No lines"))

        returns = self.order_line_ids.filtered(lambda r: r.qty_return > 0)
        if not returns:
            raise ValidationError(_("No line to return picking"))

        # create pickings & moves (your method creates moves with field 'return_line_id')
        self.create_picking_returns(returns)
        self.state = 'done'

        for order in self:
            for line in order.order_line_ids:
                barcode = getattr(line, "x_scanned_barcode", False)
                uom = line.product_uom
                description = line.name if line.name else (
                    f"{line.product_id.display_name} X {uom.name}"
                    if uom and uom.name.lower() != "unit"
                    else line.product_id.display_name
                )

                stock_moves = self.env['stock.move'].with_context(skip_barcode_uom=True).search([
                    ('return_line_id', '=', line.id)
                ])
                _logger.info("Found stock_moves for purchase return line %s: %s", line.id, stock_moves.ids)

                for move in stock_moves:
                    _logger.info("Updating move %s", move.id)
                    move.write({
                        'x_scanned_barcode': barcode,
                        'name': description,
                        'description_picking': description,
                        'product_uom_qty': line.qty_return,
                        'product_uom': uom.id,
                    })

                    for move_line in move.move_line_ids:
                        _logger.info("Updating move_line %s (move %s)", move_line.id, move.id)
                        move_line.write({
                            'x_scanned_barcode': barcode,
                            'description': description,
                            'qty_done': line.qty_return,
                            'product_uom_id': uom.id,
                        })



class PurchaseReturnLine(models.Model):
    _inherit = 'purchase.return.line'

    x_scanned_barcode = fields.Char(string="Barcode")
    is_barcode_price_set = fields.Boolean(string="Is Barcode Price Set", default=False)
    name = fields.Char(string="Description")

    # @api.constrains('qty_return')
    # def _check_product_uom_qty(self):
    #     for line in self:
    #         if line.qty_return <= 0:
    #             raise ValidationError("The quantity must be greater than 0.")

    # ========== Onchange: Product / Qty Return ==========
    @api.onchange('product_id', 'qty_return')
    def get_unit_uom(self):
        """
        Set default UoM and price when product or qty changes,
        but DO NOT override UoM if set via barcode scan.
        """
        for line in self:
            #  Skip resetting if barcode already set the UoM
            if line.is_barcode_price_set:
                continue

            if line.product_id:
                # Default to product's base UoM
                # line.product_uom = line.product_id.uom_id.id
                line.price_unit = line.product_id.lst_price

            if self.env.context.get('skip_uom_logic'):
                continue

            # if line.product_id and line.qty_return:
            #     qty_entered = line.qty_return
            #     all_uoms = line.product_id.barcode_uom_ids.mapped('uom_id')
            #     match_found = False

            #     for uom in all_uoms:
            #         match = re.search(r'\d+', uom.name)
            #         if match:
            #             multiplier = int(match.group(0))
            #             _logger.info(f"UOM Name: {uom.name} → Multiplier: {multiplier}")

            #             if multiplier == int(qty_entered):
            #                 _logger.info(f"=== MATCH FOUND: QTY={qty_entered}, UOM={uom.name} ===")
            #                 line.product_uom = uom.id

            #                 # Prevent recursion
            #                 line = line.with_context(skip_uom_logic=True)
            #                 line.qty_return = 1
            #                 match_found = True
            #                 break


    # ========== Onchange: UoM / Qty Return ==========
    @api.onchange('product_uom', 'qty_return')
    def onchange_uom(self):
        for line in self:
            if not line.product_id or not line.product_uom:
                continue

            product = line.product_id
            partner = line.partner_id
            selected_uom = line.product_uom
            base_uom = product.uom_id 
            sellers = product.seller_ids

            barcode_line = self.env['product.barcode.uom'].search([
                ('product_id', '=', product.product_tmpl_id.id),
                ('uom_id', '=', selected_uom.id)
            ], limit=1)

            if not (barcode_line and line.x_scanned_barcode):
                continue

            line.x_scanned_barcode = barcode_line.barcode

            seller_line = False

            seller_line = sellers.filtered(
                lambda s:
                    (not partner or s.name.id == partner.id) and s.product_uom.id == selected_uom.id)[:1]

            if not seller_line and selected_uom == base_uom:
                seller_line = sellers.filtered(lambda s: not partner or s.name.id == partner.id)[:1] or sellers[:1]

            if not seller_line and selected_uom != base_uom:
                unit_seller = sellers.filtered(lambda s: s.product_uom.id == base_uom.id and (not partner or s.name.id == partner.id))[:1] or sellers.filtered(lambda s: s.product_uom.id == base_uom.id)[:1]

                if unit_seller:
                    line.price_unit = unit_seller.price * selected_uom.factor_inv
                    _logger.info(
                        f"=== CHILD UOM FALLBACK: {unit_seller.price} × {selected_uom.factor_inv} ==="
                    )
                    seller_line = False  

            if seller_line:
                line.price_unit = seller_line.price
                _logger.info(
                    f"=== SELLER PRICE USED: {seller_line.price} "
                    f"(Vendor={seller_line.name.display_name}, "
                    f"UOM={seller_line.product_uom.name}) ==="
                )

            if 'UNIT' not in (selected_uom.name or '').upper():
                line.name = f"{product.name} X {selected_uom.name}"
            else:
                line.name = product.name

    # @api.onchange('product_uom', 'qty_return')
    # def onchange_uom(self):
    #     product_name = self.product_id.name or ''
    #     uom_name = self.product_uom.name or ''

    #     if self.product_id and self.product_uom:
    #         uom_line = self.env['product.barcode.uom'].search([
    #             ('product_id', '=', self.product_id.product_tmpl_id.id),
    #             ('uom_id', '=', self.product_uom.id)
    #         ], limit=1)


    #         # if uom_line:
    #         #     self.x_scanned_barcode = uom_line.barcode

    #         #     if uom_line and uom_line.sale_price:
    #         #         self.price_unit = 11.0

    #         #         # self.price_unit = uom_line.sale_price
    #         #         _logger.info(f"=== UNIT PRICE UPDATED ON UOM CHANGE: {uom_line.sale_price} for UOM={self.product_uom.name} ===")
    #         #     else:
    #         #         # self.price_unit = self.product_id.uom_id._compute_price(
    #         #         #     self.product_id.list_price, self.product_uom
    #         #         # )
    #         #         self.price_unit = 9.0
    #         #         _logger.info(f"=== UNIT PRICE FALLBACK (converted): {self.price_unit} ===")


    #     if 'UNIT' not in uom_name.upper():
    #         self.name = f"{product_name} X {uom_name}"
    #     else:
    #         self.name = product_name

    # ========== Onchange: Barcode ==========
    @api.onchange('x_scanned_barcode')
    def _onchange_x_scanned_barcode(self):
        self.is_barcode_price_set = False
        if not self.x_scanned_barcode:
            return

        product, barcode_line = None, None
        barcode_line = self.env['product.barcode.uom'].search([
            ('barcode', '=', self.x_scanned_barcode)
        ], limit=1)

        if barcode_line:
            _logger.info("=== FOUND BARCODE LINE ===")
            _logger.info(f"Barcode: {barcode_line.barcode}")
            _logger.info(f"UOM: {barcode_line.uom_id.name} (ID: {barcode_line.uom_id.id})")
            _logger.info(f"Sale price: {barcode_line.sale_price}")

            product = self.env['product.product'].search([
                ('product_tmpl_id', '=', barcode_line.product_id.id)
            ], limit=1)

        elif len(self.x_scanned_barcode.strip()) <= 5:
            product = self.env['product.product'].search([
                ('default_code', '=', self.x_scanned_barcode)
            ], limit=1)

        else:
            product = self.env['product.product'].search([
                ('barcode', '=', self.x_scanned_barcode)
            ], limit=1)

        if product:
            self.is_barcode_price_set = True
            self.product_id = product.id

            if barcode_line:
                #  Force UoM from barcode line
                self.product_uom = barcode_line.uom_id.id
                #  Price
                if barcode_line.sale_price:
                    self.price_unit = barcode_line.sale_price
                else:
                    self.price_unit = product.uom_id._compute_price(
                        product.list_price, self.product_uom
                    )
            else:
                # fallback to seller logic ONLY if no barcode match
                seller = next((line for line in product.seller_ids if line.name == self.partner_id), None)
                if not seller and product.seller_ids:
                    seller = product.seller_ids[0]
                if seller:
                    _logger.info(f"Using seller: {seller.name.display_name}")
                    self.product_uom = seller.product_uom.id
                    self.product_qty = 0.0
                    self.price_unit = seller.price

        #  Update description
        if self.product_id and self.product_uom:
            if barcode_line and barcode_line.description:
                self.name = barcode_line.description
            else:
                if 'UNIT' not in (self.product_uom.name or '').upper():
                    self.name = f"{self.product_id.name} X {self.product_uom.name}"
                else:
                    self.name = self.product_id.name

        #  Restrict UoM domain
        if self.product_id:
            allowed_uoms = self.product_id.barcode_uom_ids.mapped('uom_id').ids
            return {
                'domain': {'product_uom': [('id', 'in', allowed_uoms)]}
            }
