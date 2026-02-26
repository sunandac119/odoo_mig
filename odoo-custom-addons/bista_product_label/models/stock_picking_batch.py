from odoo import fields, models, api


class ModelName(models.Model):
    _inherit = "stock.picking.batch"

    def get_qr_batch_operations_settings(self):
        IrParamSudo = self.env['ir.config_parameter'].sudo()

        batch_operations_qr_code_settings = IrParamSudo.get_param('bista_product_label.use_qr_code_batch_operations')

        return batch_operations_qr_code_settings
