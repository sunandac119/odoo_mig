from odoo import models, fields


class ProductTemplate(models.Model):
    _inherit = 'product.template'

    parent_id = fields.Many2one('product.template', string='Parent Product', index=True, ondelete='cascade')
    child_ids = fields.One2many('product.template', 'parent_id', string='Child Products')


class ProductProduct(models.Model):
    _inherit = 'product.product'

    parent_id = fields.Many2one(related='product_tmpl_id.parent_id', string='Parent Product', store=True)
