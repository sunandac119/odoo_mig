from odoo import api, fields, models


class ProductTemplateAttributeValue(models.Model):
    _inherit = 'product.template.attribute.value'

    is_synced_with_server = fields.Boolean(string="Is Synced with server?",default=False)
    remote_server_db_id = fields.Integer(string="Remote Server DB Id")