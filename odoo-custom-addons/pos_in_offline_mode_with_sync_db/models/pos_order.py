from odoo import api, fields, models


class PosOrder(models.Model):
    _inherit = 'pos.order'

    @api.model
    def create(self, values):
        old_name = values.get('name')
        res = super().create(values)
        if self.env.company.current_running_db_server == 'remote_server' and old_name:
            res.name = old_name
        return res

class Resusers(models.Model):
    _inherit = 'res.users'

    @api.model
    def create(self, values):
        # old_name = values.get('name')
        res = super().create(values)
        # if self.env.company.current_running_db_server == 'remote_server' and old_name:
        #     res.name = old_name
        return res