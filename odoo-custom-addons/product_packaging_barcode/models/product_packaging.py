from odoo import fields, models, api


class ProductPackaging(models.Model):
    _inherit = "product.product"

    _sql_constraints = [
            ('barcode_uniq', 'unique(barcode)', 'Bar-code  No must be unique !'),
         ]