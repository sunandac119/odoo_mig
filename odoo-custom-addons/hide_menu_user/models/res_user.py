# -*- coding: utf-8 -*-
from odoo import models, fields, api

class HideMenuUser(models.Model):
    _inherit = 'res.users'

    hide_menu_ids = fields.Many2many(
        'ir.ui.menu',
        string="Menu",
        store=True,
        help='Select menu items that need to be hidden for this user.'
    )
    is_admin = fields.Boolean(compute='_get_is_admin')

    @api.model
    def create(self, vals):
        """Handle both single and batch creates, and sync restrict_user_ids."""
        # Create records first
        records = super(HideMenuUser, self).create(vals)
        # Ensure 'records' is a recordset (create can return single or multi)
        for user in records:
            if user.hide_menu_ids:
                # Add user to restrict_user_ids of selected menus
                user.hide_menu_ids.sudo().write({
                    'restrict_user_ids': [(4, user.id)]
                })
            user.clear_caches()
        return records

    def write(self, vals):
        """
        Make it safe for multi-record writes and keep ir.ui.menu.restrict_user_ids
        synchronized with this user's hide_menu_ids (adds and removals).
        """
        # Capture old state per user BEFORE write
        old_map = {u.id: set(u.hide_menu_ids.ids) for u in self}

        res = super(HideMenuUser, self).write(vals)

        # Compute delta AFTER write and sync menus
        for user in self:
            new_ids = set(user.hide_menu_ids.ids)
            old_ids = old_map.get(user.id, set())

            to_add_ids = list(new_ids - old_ids)
            to_remove_ids = list(old_ids - new_ids)

            # Add links (no replace)
            if to_add_ids:
                self.env['ir.ui.menu'].browse(to_add_ids).sudo().write({
                    'restrict_user_ids': [(4, user.id)]
                })

            # Remove links if a menu was unselected for this user
            if to_remove_ids:
                self.env['ir.ui.menu'].browse(to_remove_ids).sudo().write({
                    'restrict_user_ids': [(3, user.id)]
                })

        # Clear caches so UI updates instantly
        self.clear_caches()
        return res

    def _get_is_admin(self):
        """Hide the tab for the main Administrator only."""
        for rec in self:
            rec.is_admin = rec.id == self.env.ref('base.user_admin').id


class RestrictMenu(models.Model):
    _inherit = 'ir.ui.menu'

    restrict_user_ids = fields.Many2many('res.users')
