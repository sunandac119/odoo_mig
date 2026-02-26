# -*- coding: utf-8 -*-
# Powered by Kanak Infosystems LLP.
# © 2020 Kanak Infosystems LLP. (<https://www.kanakinfosystems.com>).

from odoo import models, fields, api, _


class ProductPricelistItem(models.Model):
    _inherit = "product.pricelist.item"

    product_packaging_id = fields.Many2one("product.packaging", string="Packaging", ondelete='cascade')
    uom_name = fields.Many2one('uom.uom', string="UOM", related="product_id.uom_id")

    @api.onchange('product_id')
    def _onchange_product_id(self):
        res = super(ProductPricelistItem, self)._onchange_product_id()
        self.uom_name = self.product_id.uom_id
        return res

    @api.onchange('product_packaging_id')
    def _compute_min_qty(self):
        self.min_quantity = self.product_packaging_id.qty

    @api.depends('applied_on', 'categ_id', 'product_tmpl_id', 'product_id', 'compute_price', 'fixed_price', 'pricelist_id', 'percent_price', 'price_discount', 'price_surcharge')
    def _get_pricelist_item_name_price(self):
        res = super(ProductPricelistItem, self)._get_pricelist_item_name_price()
        for item in self:
            if item.product_packaging_id and item.applied_on == '0_product_variant':
                item.name = _("Packaging: [%s][%s]%s") % (item.product_packaging_id.name, str(item.product_packaging_id.qty), item.product_packaging_id.product_id.display_name)
        return res
