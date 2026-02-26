from odoo import api, fields, models


class ProductTemplate(models.Model):
    _inherit = 'product.template'

    lhdn_classification_id = fields.Many2one('lhdn.item.classification.code', string="LHDN Classification")
