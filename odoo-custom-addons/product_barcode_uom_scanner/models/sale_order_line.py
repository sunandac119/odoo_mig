from odoo import api, fields, models

class SaleOrderLine(models.Model):
    _inherit = 'sale.order.line'

    input_barcode = fields.Char(string='Scan Barcode')

    @api.onchange('input_barcode')
    def _onchange_input_barcode(self):
        if not self.input_barcode:
            return

        barcode_line = self.env['f.pos.multi.uom.barcode.lines'].search([
            ('barcode', '=', self.input_barcode)
        ], limit=1)

        if barcode_line:
            product = self.env['product.product'].search([
                ('product_tmpl_id', '=', barcode_line.product_tmpl_id.id)
            ], limit=1)

            if product:
                # STEP 0: Clear fields first to avoid JS lock or reset
                self.product_id = False
                self.product_uom = False

                # STEP 1: Set UoM first
                self.product_uom = barcode_line.uom_id.id

                # STEP 2: Set product
                self.product_id = product.id

                # STEP 3: Set price only
                self.price_unit = barcode_line.sale_price

        self.input_barcode = False
