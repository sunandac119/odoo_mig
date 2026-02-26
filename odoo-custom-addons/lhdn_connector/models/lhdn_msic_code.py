from odoo import api, fields, models


class LhdnMsicCode(models.Model):
    _name = 'lhdn.msic.code'
    _description = 'LhdnMsicCode'
    _rec_names_search = ['name', 'code']


    name = fields.Char(string="Description")
    code = fields.Char(string="Code")
