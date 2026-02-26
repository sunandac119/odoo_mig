# -*- coding: utf-8 -*-
# Powered by Kanak Infosystems LLP.
# © 2020 Kanak Infosystems LLP. (<https://www.kanakinfosystems.com>).
from odoo import models, fields


class AccountMoveLine(models.Model):
    _inherit = "account.move.line"

    product_packaging_id = fields.Many2one('product.packaging', string="Packaging")
    product_packaging_qty = fields.Float(string="Packaging Quantity")
