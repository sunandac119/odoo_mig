from odoo import api, fields, models


class LhdnItemClassificationCode(models.Model):
    _name = 'lhdn.item.classification.code'
    _description = 'LhdnItemClassificationCode'
    _rec_names_search = ['name', 'code']

    name = fields.Char(string="Description")
    code = fields.Char(string="Code")
