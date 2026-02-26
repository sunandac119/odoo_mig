from odoo import api, fields, models


class ProductProduct(models.Model):
    _inherit = 'product.product'

    external_system_db_id = fields.Char('External System DB Id')
