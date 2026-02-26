# -*- coding: utf-8 -*-

from odoo import models, fields, api, tools
import logging
from odoo.http import request
from decorator import decorator
_logger = logging.getLogger(__name__)

# Hide Menu From Users 
class ResUsers(models.Model):
    _inherit = 'res.users'
    _description = 'Res Users'

    # Hide Menu From Users
    menu_id= fields.Many2many('ir.ui.menu', string='Menus')
    report_access_ids = fields.Many2many('ir.actions.report', string='Reports')

    def write(self, vals):
        res = super(ResUsers, self).write(vals)
        self.env['ir.ui.menu'].load_menus(debug=1)
        self.clear_caches()
        return res

    def _get_is_admin(self):
        for rec in self:
            rec.is_admin = False
            if rec.id == self.env.ref('base.user_admin').id:
                rec.is_admin = True
    is_admin = fields.Boolean(compute=_get_is_admin)

class ResGroups(models.Model):
    _inherit = 'res.groups'
    _description = 'Res Groups'

    # Hide Menu From Groups
    menu_ids= fields.Many2many('ir.ui.menu', string='Menus')
    report_ids = fields.Many2many('ir.actions.report', string='Reports')

    def write(self, vals):
        res = super(ResGroups, self).write(vals)
        self.env['ir.ui.menu'].load_menus(debug=1)
        self.clear_caches()
        return res

class IrUiMenu(models.Model):
    _inherit="ir.ui.menu"
    _description = 'Ir Ui Menu'

    def write(self, vals):
        res = super(IrUiMenu, self).write(vals)
        request.env['ir.ui.menu'].load_menus(request.session.debug)
        self.clear_caches()
        return res

    # Menu IDS Hide From Users and Groups
    @api.model
    @tools.ormcache('frozenset(self.env.user.groups_id.ids)', 'debug')
    def _visible_menu_ids(self, debug=False):
        menus = super(IrUiMenu, self)._visible_menu_ids(debug)
        menu_ids = []

        user = self.env.user

        if user.menu_id and not user.has_group('base.group_system'):
            menu_ids.extend(menu.id for menu in user.menu_id)

        res_group_menu = self.env['res.groups'].search([('users', 'in', user.id), ('menu_ids', '!=', False)])
        if res_group_menu and not user.has_group('base.group_system'):
            menu_ids.extend(res_group_menu.menu_ids.ids)

        menus.difference_update(menu_ids)

        return menus

    # Report IDS Hide 
    @api.model
    @tools.ormcache_context('self._uid', 'debug', keys=('lang',))
    def load_menus(self, debug):
        reports_user = False
        reports_group = False
        
        res_user1 = self.env['res.users'].search([('id', '!=', self.env.user.id),('report_access_ids', '!=', False),('parent_id','=',False)])
        for user1 in res_user1:
            reports_user = user1.report_access_ids
            if res_user1:
                if reports_user:
                    reports_user.create_action()

        res_user = self.env['res.users'].search([('id', '=', self.env.user.id),('report_access_ids', '!=', False),('parent_id','=',False)])
        for user in res_user:
            reports_user = user.report_access_ids
            if res_user:
                if reports_user:
                    reports_user.unlink_action()

        res_group = self.env['res.groups'].search([('users', '=', self.env.user.id),('report_ids', '!=', False)])
        res_group1 = self.env['res.groups'].search([('users', '!=', self.env.user.id),('report_ids', '!=', False)])
        for group in res_group:
            reports_group = group.report_ids
            if res_group:
                if reports_group:
                    reports_group.unlink_action()
                    
        for group1 in res_group1:
            reports_group1 = group1.report_ids
            if res_group1:
                if reports_group1:
                    if res_user and res_group:
                        if reports_user:
                            repos = self.env['ir.actions.report'].search([('id', 'not in', reports_user.ids),('id', 'not in', reports_group.ids)])
                            repos.create_action()
                        else:
                            reports_group1.create_action()
                    else:
                        if reports_user:
                            repots = self.env['ir.actions.report'].search([('id', 'not in', reports_user.ids)])
                            repots.create_action()
                        else:
                            reports_group1.create_action()

        ir_act_report = self.env['ir.actions.report'].search([('users_ids', '=', self.env.user.id)])
        ir_act_report1 = self.env['ir.actions.report'].search([('users_ids', '!=', self.env.user.id)])
        if ir_act_report:
            ir_act_report.unlink_action()
        if ir_act_report1:
            if res_user and res_group and ir_act_report:
                if reports_user or reports_group:
                    report_obj = self.env['ir.actions.report'].search([('id', 'not in', reports_user.ids),('id', 'not in', reports_group.ids),('id', 'not in', ir_act_report.ids)])
                    report_obj.create_action()
                else:
                    ir_act_report1.create_action()
            elif res_user and res_group:
                if reports_user or reports_group:
                    reports_group_obj = self.env['ir.actions.report'].search([('id', 'not in', reports_user.ids),('id', 'not in', reports_group.ids)])
                    reports_group_obj.create_action()
                else:
                    ir_act_report1.create_action()
            else:
                if reports_user or reports_group or ir_act_report:
                    if reports_group:
                        hide_report = self.env['ir.actions.report'].search([('id', 'not in', reports_group.ids)])
                        hide_report.create_action()
                    if reports_user:
                        hide_report = self.env['ir.actions.report'].search([('id', 'not in', reports_user.ids)])
                        hide_report.create_action()
                    if ir_act_report:
                        hide_report = self.env['ir.actions.report'].search([('id', 'not in', ir_act_report.ids)])
                        hide_report.create_action()

                else:
                    ir_act_report1.create_action()
        return super(IrUiMenu, self).load_menus(request.session.debug)
