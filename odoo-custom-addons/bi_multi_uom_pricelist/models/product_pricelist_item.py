# -*- coding: utf-8 -*-
# Part of BrowseInfo. See LICENSE file for full copyright and licensing details.

from odoo import api, fields, models, tools, _
from odoo.exceptions import UserError, ValidationError
from odoo.tools import format_datetime
from odoo.tools.misc import formatLang, get_lang



class ProductPricelistItems(models.Model):
    _inherit = "product.pricelist.item"

    uom_id = fields.Many2one('uom.uom', 'Pricelist UOM', required=True)

    @api.onchange('product_tmpl_id')
    def _onchange_product_tmpl_id(self):
        if self.product_tmpl_id:
            # Update the domain for uom_id based on the selected product template
            return {'domain': {'uom_id': [('category_id', '=', self.product_tmpl_id.uom_id.category_id.id)]}}

    _sql_constraints = [
        ('check_uom_id', 'CHECK(uom_id IS NOT NULL)', _('Please select a Price list UOM.')),
    ]