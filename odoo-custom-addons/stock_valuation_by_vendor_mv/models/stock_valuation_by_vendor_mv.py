# -*- coding: utf-8 -*-
from odoo import models, fields

class StockValuationByVendorMv(models.Model):
    _name = 'stock.valuation.by.vendor.mv'
    _description = 'Auto Generated View'
    _auto = False

    name = fields.Char("Name")

    def init(self):
        self.env.cr.execute("SELECT 1 WHERE 1=0")  # Dummy SQL