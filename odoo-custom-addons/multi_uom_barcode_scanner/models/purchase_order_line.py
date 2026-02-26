from odoo import models, fields, api


class PurchaseOrderLine(models.Model):
    _inherit = 'purchase.order.line'

    x_scanned_barcode = fields.Char(string="Scanned Barcode")
    _barcode_uom_id = fields.Many2one('uom.uom', string="Barcode UOM", store=False)
    _barcode_price = fields.Float(string="Barcode Price", store=False)

    @api.onchange('x_scanned_barcode')
    def _onchange_x_scanned_barcode(self):
        if not self.x_scanned_barcode:
            self._barcode_uom_id = False
            self._barcode_price = 0.0
            return

        # Search directly in barcode lines
        barcode_line = self.env['f.pos.multi.uom.barcode.lines'].search([
            ('barcode', '=', self.x_scanned_barcode)
        ], limit=1)

        if barcode_line:
            # Find product variant
            product = self.env['product.product'].search([
                ('product_tmpl_id', '=', barcode_line.uom_barcode.id)
            ], limit=1)

            if product:
                # Store barcode values in temporary fields
                self._barcode_uom_id = barcode_line.uom.id

                # Get price from barcode line - use sale_price field
                barcode_price = barcode_line.sale_price if barcode_line.sale_price > 0 else product.standard_price

                self._barcode_price = barcode_price

                # Set product first
                self.product_id = product.id

                # Set UOM from barcode
                self.product_uom = barcode_line.uom.id

                # Set price from barcode
                self.price_unit = barcode_line.uom.id

                # Set quantity if not set
                if not self.product_qty:
                    self.product_qty = 1.0
            else:
                self._barcode_uom_id = False
                self._barcode_price = 0.0
        else:
            self._barcode_uom_id = False
            self._barcode_price = 0.0

    @api.onchange('product_id')
    def _onchange_product_id(self):
        # If we have barcode values stored, use them
        if self.x_scanned_barcode and self._barcode_uom_id:
            self.product_uom = self._barcode_uom_id.id
            if self._barcode_price > 0:
                self.price_unit = self._barcode_price
            return

        # Normal product change behavior
        if self.product_id:
            self.product_uom = self.product_id.uom_po_id.id or self.product_id.uom_id.id
            self.price_unit = self.product_id.standard_price

    @api.onchange('product_uom')
    def _onchange_product_uom(self):
        """Override UOM change to preserve barcode UOM"""
        if self.x_scanned_barcode and self._barcode_uom_id:
            if self.product_uom != self._barcode_uom_id:
                self.product_uom = self._barcode_uom_id.id
            return

        # Call parent method for normal cases
        try:
            return super()._onchange_product_uom()
        except:
            pass

    @api.onchange('price_unit')
    def _onchange_price_unit(self):
        """Override price change to preserve barcode price initially"""
        if self.x_scanned_barcode and self._barcode_price > 0:
            # Allow price change after initial setting
            # This prevents immediate override but allows manual editing
            pass

        # Call parent method for normal cases
        try:
            return super()._onchange_price_unit()
        except:
            pass