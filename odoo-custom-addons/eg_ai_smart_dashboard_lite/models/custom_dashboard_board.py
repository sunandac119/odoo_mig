from odoo import models, fields, api


class CustomDashboardBoard(models.Model):
    _name = 'custom.dashboard.board'
    _description = 'Custom Dashboard Board'

    name = fields.Char(string='Name')
    custom_dashboard_items_ids = fields.One2many(comodel_name='eg.custom.dashboard.item',
                                                 inverse_name='custom_dashboard_board_id', string='Dashboard Items')
    dashboard_menu_name = fields.Char(string='Menu Name')
    # ir_ui_menu_id = fields.Many2one(comodel_name='ir.ui.menu', string='Menu show', domain="[('parent_id','=',False)]")
    # ir_action_client_id = fields.Many2one(comodel_name='ir.actions.client', string='Action Client')
    # menu_id = fields.Many2one(comodel_name='ir.ui.menu')
    # res_group_ids = fields.Many2many(comodel_name='res.groups', string='Access Groups')
    count_total_items = fields.Float(string='Total Items', compute='_compute_count_total_items')
    color = fields.Char(string='Color')

    # chart_translate_horizontal = fields.Float('Chart Translate Horizontal Position')
    # chart_translate_vertical = fields.Float('Chart Translate Vertical Position')
    # view_arch = fields.Text('View Architecture')
    @api.depends('custom_dashboard_items_ids')
    def _compute_count_total_items(self):
        for rec in self:
            rec.count_total_items = len(rec.custom_dashboard_items_ids.ids)

    def get_main_dashboard_view(self):
        action = self.env.ref('eg_ai_smart_dashboard_lite.custom_dashboard_client_action').read()[0]
        params = {
            'model': 'custom.dashboard.board',
            'dashboard_board_id': self.id,
            # 'nomenclature_id': [self.env.company.nomenclature_id],
        }
        return dict(action, target='main', params=params)

    @api.model
    def _update_chart_item_or_create_return(self, dashboard_id):
        action = self.env.ref('eg_ai_smart_dashboard_lite.custom_dashboard_client_action').read()[0]
        params = {
            'model': 'custom.dashboard.board',
            'dashboard_board_id': dashboard_id,
        }
        return dict(action, target='main', params=params)

    @api.model
    def get_dashboard_items_lines(self, dashboard_board_id):
        dashboard_item_ids = self.search([('id', '=', dashboard_board_id)])
        group_custom_dashboard_manager = self.user_has_groups('eg_ai_smart_dashboard_lite.custom_dashboard_manager')
        return_dict = {
            'name': dashboard_item_ids.name,
            'dashboard_item_ids': dashboard_item_ids.custom_dashboard_items_ids.ids,
            'group_custom_dashboard_manager': group_custom_dashboard_manager,
        }
        return return_dict

    # @api.model
    # def create(self, vals):
    #     res = super(CustomDashboardBoard, self).create(vals)
    #     if 'ir_ui_menu_id' in vals and 'dashboard_menu_name' in vals:
    #         action_id = {
    #             'name': vals['dashboard_menu_name'] + " Action",
    #             'res_model': 'custom.dashboard.board',
    #             'tag': 'custom_dashboard_client_action',
    #             'params': {'dashboard_board_id': res.id},
    #         }
    #         res.ir_action_client_id = self.env['ir.actions.client'].sudo().create(action_id)
    #
    #         res.menu_id = self.env['ir.ui.menu'].sudo().create({
    #             'name': vals['dashboard_menu_name'],
    #             'active': True,
    #             'parent_id': vals['ir_ui_menu_id'],
    #             'action': "ir.actions.client," + str(res.ir_action_client_id.id),
    #             'groups_id': vals.get('res_group_ids', False),
    #             'sequence': 10,
    #         })
    #     return res
