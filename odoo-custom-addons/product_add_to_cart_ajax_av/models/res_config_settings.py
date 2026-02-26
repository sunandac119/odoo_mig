# -*- coding: utf-8 -*-

from odoo import models, fields

class ResConfigSettings(models.TransientModel):
	_inherit = 'res.config.settings'

	is_cart_ajax_field = fields.Boolean("Add to Cart Using Ajax",related='website_id.is_cart_ajax_field',default=True,readonly=False)