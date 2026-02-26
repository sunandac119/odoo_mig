
from odoo import models, api

class ResUsers(models.Model):
    _inherit = 'res.users'

    @api.model
    def get_user_context(self):
        ctx = super().get_user_context()
        ctx['allowed_branch_ids'] = self.env.user.branch_ids.ids
        return ctx
