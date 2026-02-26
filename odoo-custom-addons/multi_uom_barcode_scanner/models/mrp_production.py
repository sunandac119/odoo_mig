from odoo import models, fields, api


class MrpProduction(models.Model):
    _inherit = 'mrp.production'

    x_scanned_barcode = fields.Char(string="Scanned Barcode")
    _barcode_uom_id = fields.Many2one('uom.uom', string="Barcode UOM", store=False)

    @api.onchange('x_scanned_barcode')
    def _onchange_x_scanned_barcode(self):
        if not self.x_scanned_barcode:
            self._barcode_uom_id = False
            return

        print(f"=== SCANNING BARCODE: {self.x_scanned_barcode} ===")

        # Search directly in barcode lines
        barcode_line = self.env['f.pos.multi.uom.barcode.lines'].search([
            ('barcode', '=', self.x_scanned_barcode)
        ], limit=1)

        if barcode_line:
            print(f"=== FOUND BARCODE LINE ===")
            print(f"UOM from barcode: {barcode_line.uom.name} (ID: {barcode_line.uom.id})")

            # Find product variant
            product = self.env['product.product'].search([
                ('product_tmpl_id', '=', barcode_line.uom_barcode.id)
            ], limit=1)

            if product:
                print(f"=== SETTING VALUES ===")
                print(f"Product: {product.name}")
                print(f"Setting UOM to: {barcode_line.uom.name}")

                # Store the barcode UOM in temporary field
                self._barcode_uom_id = barcode_line.uom.id

                # Set product first
                self.product_id = product.id

                # Force set UOM after product
                self.product_uom_id = barcode_line.uom.id

                # Set quantity if not set
                if not self.product_qty:
                    self.product_qty = 1.0

                print(f"=== VALUES SET ===")
                print(f"Barcode UOM stored: {self._barcode_uom_id.name if self._barcode_uom_id else 'None'}")
            else:
                print(f"=== NO PRODUCT FOUND ===")
                self._barcode_uom_id = False
        else:
            print(f"=== NO BARCODE LINE FOUND ===")
            self._barcode_uom_id = False

    @api.onchange('product_id')
    def _onchange_product_id(self):
        print(f"=== PRODUCT ID CHANGED ===")
        print(f"Barcode: {self.x_scanned_barcode}")
        print(f"Barcode UOM: {self._barcode_uom_id.name if self._barcode_uom_id else 'None'}")

        # If we have a barcode UOM stored, use it
        if self.x_scanned_barcode and self._barcode_uom_id:
            print(f"=== PRESERVING BARCODE UOM: {self._barcode_uom_id.name} ===")
            self.product_uom_id = self._barcode_uom_id.id
            return

        # Normal product change behavior - call parent method if exists
        try:
            result = super()._onchange_product_id()
            return result
        except:
            # Fallback if parent method doesn't exist
            if self.product_id:
                self.product_uom_id = self.product_id.uom_id.id

    @api.onchange('product_uom_id')
    def _onchange_product_uom_id(self):
        """Override UOM change to preserve barcode UOM"""
        if self.x_scanned_barcode and self._barcode_uom_id:
            print(f"=== UOM ONCHANGE - PRESERVING BARCODE UOM ===")
            if self.product_uom_id != self._barcode_uom_id:
                self.product_uom_id = self._barcode_uom_id.id
            return

        # Call parent method for normal cases
        try:
            return super()._onchange_product_uom_id()
        except:
            pass