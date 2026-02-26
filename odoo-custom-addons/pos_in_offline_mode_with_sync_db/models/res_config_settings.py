from odoo import api, fields, models


class ResConfigSettings(models.TransientModel):
    _inherit = 'res.config.settings'

    current_running_db_server = fields.Selection(related="company_id.current_running_db_server",
                                                 string="Current Running Server DB",
                                                 readonly=False)
    remote_server_url = fields.Char(related="company_id.remote_server_url", string="Remote Server Url", readonly=False)
    remote_server_db = fields.Char(related="company_id.remote_server_db", string="Remote Server DB", readonly=False)
    remote_server_admin_user_name = fields.Char(related="company_id.remote_server_admin_user_name",
                                                string="Remote Server Admin User Name",
                                                readonly=False)
    remote_server_admin_user_password = fields.Char(related="company_id.remote_server_admin_user_password",
                                                    string="Remote Server Admin User Passwords",
                                                    readonly=False)
    remote_server_last_synced_data_time = fields.Datetime(related="company_id.remote_server_last_synced_data_time",
                                                          string="Remote Server Data Last Synced Date Time",
                                                          readonly=False)
