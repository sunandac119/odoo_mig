from odoo import api, fields, models


class SaleOrder(models.Model):
    _inherit = 'sale.order'

    external_system_db_id = fields.Char('External System DB Id')
