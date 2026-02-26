# -*- coding: utf-8 -*-
from odoo import fields, models

class ProductTemplate(models.Model):
    _inherit = "product.template"

    department = fields.Selection(
        selection=[
            ("01", "01 Jajan"),
            ("02", "02 Chocolate"),
            ("03", "03 Housebrand"),
            ("04", "04 Repacking"),
        ],
        string="Department",
        index=True,
        help="Internal department classification for this product.",
    )