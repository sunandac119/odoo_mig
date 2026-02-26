# -*- coding: utf-8 -*-
from odoo import models, fields, api
from odoo.exceptions import UserError
from odoo.exceptions import ValidationError
from datetime import date

class SaleOrderLine(models.Model):
    _inherit = 'sale.order.line'

    barcode = fields.Char(string="Barcode")
    custom_unit_price = fields.Float(string="Custom Unit Price")

    @api.onchange('barcode')
    def _onchange_barcode(self):
        if self.barcode:
            BarcodeLine = self.env['f.pos.multi.uom.barcode.lines'].search([
                ('barcode', '=', self.barcode)
            ], limit=1)
            if BarcodeLine:
                self.product_uom = BarcodeLine.uom_id

                get_uom = BarcodeLine.uom_id
                if BarcodeLine.product_tmpl_id:
                    product = self.env['product.product'].search([
                        ('product_tmpl_id', '=', BarcodeLine.product_tmpl_id.id)
                    ], limit=1)

                    if product:
                        self.product_id = product
                        today = date.today()

                        get_promition_product = self.env['product.pricelist.item'].search([
                            ('product_tmpl_id', '=', BarcodeLine.product_tmpl_id.id),
                            ('date_start', '<=', today),
                            ('date_end', '>=', today),
                            ('uom_id', '=', get_uom.id)
                        ], limit=1)
                        if get_promition_product:
                            self.custom_unit_price = (
                                get_promition_product.fixed_price if get_promition_product
                                else BarcodeLine.sale_price
                            )
                            self.product_uom=get_promition_product.uom_id
                        else:
                            pass

                    else:
                        raise UserError("No product variant found for the matching template.")
            else:
                pass

    @api.depends('custom_unit_price')
    def _compute_price_unit(self):
        for line in self:
            if line.custom_unit_price:
                line.price_unit = line.custom_unit_price

    price_unit = fields.Float(
        string='Unit Price',
        compute='_compute_price_unit',
        store=True,
    )


    @api.onchange('product_id', 'product_uom')
    def _onchange_product_id_(self):
        if self.product_id:
            get_uom_id = self.product_uom.id
            today = date.today()

            BarcodeLine = self.env['f.pos.multi.uom.barcode.lines'].search([
                ('uom_id', '=', get_uom_id),
                ('product_tmpl_id', '=', self.product_id.product_tmpl_id.id)
            ], limit=1)

            if not BarcodeLine:
                pass

            self.barcode = BarcodeLine.barcode

            get_promotion_product = self.env['product.pricelist.item'].search([
                ('product_tmpl_id', '=', BarcodeLine.product_tmpl_id.id),
                ('date_start', '<=', today),
                ('date_end', '>=', today),
                ('uom_id', '=', get_uom_id)
            ], limit=1)

            if get_promotion_product:
                self.custom_unit_price = get_promotion_product.fixed_price
            else:
                self.custom_unit_price = BarcodeLine.sale_price