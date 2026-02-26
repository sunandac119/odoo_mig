
from odoo import models, fields

class ProductUomMapping(models.Model):
    _name = 'product.uom.mapping'
    _description = 'Multi UoM Mapping'

    product_tmpl_id = fields.Many2one('product.template', string='Product Template', required=True, ondelete='cascade')
    uom_id = fields.Many2one('uom.uom', string='UoM', required=True)
    factor = fields.Float(string='Qty per UoM', required=True)
    barcode = fields.Char(string='Barcode')
    price = fields.Float(string='UoM Price')


class ProductTemplate(models.Model):
    _inherit = 'product.template'

    uom_mapping_ids = fields.One2many('product.uom.mapping', 'product_tmpl_id', string='Multi UoM')
