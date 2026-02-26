from odoo import models, fields

class StockInventory(models.Model):
    _inherit = 'stock.inventory'

    x_scan_barcode = fields.Char(string='Scan Barcode')
