# -*- coding: utf-8 -*-
# Powered by Kanak Infosystems LLP.
# © 2020 Kanak Infosystems LLP. (<https://www.kanakinfosystems.com>).

from odoo import api, fields, models, tools


class ProductPackgaing(models.Model):
    _inherit = "product.packaging"

    default = fields.Boolean(string="Default")
