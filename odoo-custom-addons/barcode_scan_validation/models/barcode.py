# -*- coding: utf-8 -*-
from odoo import models, fields, api ,_
from odoo.exceptions import UserError
from odoo.exceptions import ValidationError


class StockInventory(models.Model):
    _inherit = 'stock.inventory.line'

    product_id = fields.Many2one('product.product',store=True)

    @api.onchange('product_id')
    def _process_barcode(self):
        for rec in self :
            if rec.product_id:
                parent_template = rec.product_id.parent_template_id
                if rec.product_id.product_tmpl_id.id != parent_template.id:
                    raise ValidationError(
                        _("The scanned product does not match the parent template ID.")
                    )





