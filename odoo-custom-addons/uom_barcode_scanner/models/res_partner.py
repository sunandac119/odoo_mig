from odoo import models, fields, api, tools
from odoo.exceptions import ValidationError
from datetime import datetime, date
import logging

_logger = logging.getLogger(__name__)


class ResPartner(models.Model):
    _inherit = 'res.partner'

    def name_get(self):
        result = []
        if self.env.context.get('show_code'):
            for partner in self:
                code = partner.x_studio_account_code or ''
                if code:
                    name = f"{code} - {partner.display_name}"
                else:
                    name = f"{partner.display_name}"
                result.append((partner.id, name.strip()))
            return result
        else:
            return super(ResPartner, self).name_get()

    @api.model
    def name_search(self, name='', args=None, operator='ilike', limit=100):
        args = args or []
        domain = []
        if name:
            # search by code OR name
            domain = ['|', ('x_studio_account_code', operator, name), ('name', operator, name)]
        partners = self.search(domain + args, limit=limit)
        return partners.name_get()