# -*- coding: utf-8 -*-

from odoo import fields,models,api, _

class Company(models.Model):
    _inherit = 'res.company'

    quantity = fields.Float('Quantity')
    amount = fields.Float('Amount')


class ResConfigSettings(models.TransientModel):
	_inherit = 'res.config.settings'
	
	quantity = fields.Float(string="Quantity :",related="company_id.quantity",readonly=False)
	amount = fields.Float(string="Amount :",related="company_id.amount",readonly=False)
