from odoo import models, fields, api


class StockMove(models.Model):
    _inherit = 'stock.move'

    x_scanned_barcode = fields.Char(string="Scanned Barcode")
    _barcode_uom_id = fields.Many2one('uom.uom', string="Barcode UOM", store=False)

    @api.onchange('x_scanned_barcode')
    def _onchange_x_scanned_barcode(self):
        if not self.x_scanned_barcode:
            self._barcode_uom_id = False
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
                # Store the barcode UOM in temporary field
                self._barcode_uom_id = barcode_line.uom.id

                # Set product first
                self.product_id = product.id

                # Set UOM from barcode
                self.product_uom = barcode_line.uom.id

                # Set quantity if not set
                if not self.product_uom_qty:
                    self.product_uom_qty = 1.0
            else:
                self._barcode_uom_id = False
        else:
            self._barcode_uom_id = False

    @api.onchange('product_id')
    def _onchange_product_id(self):
        # If we have a barcode UOM stored, use it
        if self.x_scanned_barcode and self._barcode_uom_id:
            self.product_uom = self._barcode_uom_id.id
            return

        # Normal product change behavior
        if self.product_id:
            self.product_uom = self.product_id.uom_id.id

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