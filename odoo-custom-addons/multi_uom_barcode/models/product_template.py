from odoo import models, fields, api

class ProductUomBarcode(models.Model):
    _name = 'product.uom.barcode'
    _description = 'Product Barcode per UOM'

    product_id = fields.Many2one('product.product', string='Product', required=True)
    uom_id = fields.Many2one('uom.uom', string='UoM', required=True)
    barcode = fields.Char('Barcode', required=True)
    price = fields.Float('UoM Price')

    _sql_constraints = [
        ('barcode_unique', 'unique(barcode)', 'Barcode must be unique!')
    ]

class ProductProduct(models.Model):
    _inherit = 'product.product'

    uom_barcode_ids = fields.One2many('product.uom.barcode', 'product_id', string='UoM Barcodes')

    def get_product_by_barcode(self, barcode, pricelist_id=None):
        barcode_line = self.env['product.uom.barcode'].search([('barcode', '=', barcode)], limit=1)
        if barcode_line:
            price = barcode_line.price
            if pricelist_id:
                product = barcode_line.product_id
                price = self.env['product.pricelist'].browse(pricelist_id).get_product_price(product, 1, None)
            return {
                'product_id': barcode_line.product_id.id,
                'uom_id': barcode_line.uom_id.id,
                'price': price,
            }
        return None
