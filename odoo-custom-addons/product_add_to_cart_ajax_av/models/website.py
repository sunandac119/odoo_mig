# -*- coding: utf-8 -*-

from odoo import fields, models

class Website(models.Model):
    _inherit = "website"

    is_cart_ajax_field = fields.Boolean("Add to Cart Using Ajax",default=True)