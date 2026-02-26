# -*- coding: utf-8 -*-
from odoo import models, fields, api
from odoo.exceptions import ValidationError


class ProductTemplate(models.Model):
    _inherit = 'product.template'

    pos_uom_barcode_lines = fields.One2many(
        comodel_name="f.pos.multi.uom.barcode.lines",
        inverse_name="product_tmpl_id",
        string="POS Multi UoM Barcodes"
    )


class POSMultiUoMBarcodeLines(models.Model):
    _name = 'f.pos.multi.uom.barcode.lines'
    _description = "POS Multi UoM Barcode Lines"

    product_tmpl_id = fields.Many2one(
        comodel_name="product.template",
        string="Product Template",
        required=True,
        ondelete='cascade'
    )

    uom_categ_id = fields.Many2one(
        comodel_name='uom.category',
        string='UoM Category',
        related='product_tmpl_id.uom_id.category_id',
        readonly=True,
        store=True
    )

    uom_id = fields.Many2one(
        comodel_name="uom.uom",
        string="Unit of Measure",
        required=True,
        domain="[('category_id', '=', uom_categ_id)]"
    )

    barcode = fields.Char(
        string="Barcode",
        required=True
    )

    sale_price = fields.Float(
        string="Sale Price"
    )

    _sql_constraints = [
        ('barcode_product_uom_unique',
         'unique(barcode, product_tmpl_id)',
         "This barcode already exists for this product!")
    ]
