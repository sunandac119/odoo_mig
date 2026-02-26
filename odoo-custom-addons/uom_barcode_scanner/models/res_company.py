from odoo import models, fields, api


class ResCompany(models.Model):
    _inherit = 'res.company'

    fax_number = fields.Char(string="Fax")

