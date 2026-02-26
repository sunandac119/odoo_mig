from odoo import _, fields, models, api


class StockPicking(models.Model):
    _inherit = 'stock.picking'

    def get_qr_picking_operations_settings(self):
        IrParamSudo = self.env['ir.config_parameter'].sudo()

        picking_operations_qr_code_settings = IrParamSudo.get_param('bista_product_label.use_qr_code_picking_operations')

        return picking_operations_qr_code_settings

    def action_open_label_layout(self):
        view = self.env.ref('bista_product_label.product_label_layout_form')
        return {
            'name': _('Choose Labels Layout'),
            'type': 'ir.actions.act_window',
            'res_model': 'product.label.layout',
            'views': [(view.id, 'form')],
            'target': 'new',
            'context': {
                'default_product_ids': self.move_lines.product_id.ids,
                'default_move_line_ids': self.move_line_ids.ids,
                'default_picking_quantity': 'picking'},
        }
