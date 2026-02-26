from odoo import api, fields, models
from odoo.addons.pos_in_offline_mode_with_sync_db.models.res_company import FIELDS as syncable_fields
from datetime import datetime
class ProductTemplate(models.Model):
    _inherit = 'product.template'

    syncable_fields_last_update_date_time = fields.Datetime(string="Syncable Fields Last Update On")

    @api.model
    def create(self, values):
        if self.env.company.current_running_db_server == 'remote_server':
            pt_syncable_fields = syncable_fields['product.template']
            for update_field in list(values.keys()):
                if update_field in pt_syncable_fields:
                    values.update({'syncable_fields_last_update_date_time':datetime.now()})
                    break
        res = super().create(values)
        return res

    def write(self,vals):
        if self.env.company.current_running_db_server == 'remote_server':
            pt_syncable_fields = syncable_fields['product.template']
            for update_field in list(vals.keys()):
                if update_field in pt_syncable_fields:
                    vals.update({'syncable_fields_last_update_date_time':datetime.now()})
                    break
        res = super().write(vals)
        return res
