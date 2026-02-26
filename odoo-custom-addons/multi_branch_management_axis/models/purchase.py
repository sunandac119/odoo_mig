# -*- coding: utf-8 -*-

from odoo import api, fields, _, models
import datetime
from odoo.exceptions import UserError


class PurchaseOrder(models.Model):
    _inherit = "purchase.order"

    branch_id = fields.Many2one('res.branch', string='Branch', help='The default branch for this user.',
                                context={'user_preference': True},  default=lambda self: self.env.user.branch_id.id)

    @api.model
    def _prepare_picking(self):
        print("\n inside prepere picking", self, self.branch_id)
        if not self.group_id:
            self.group_id = self.group_id.create({
                'name': self.name,
                'partner_id': self.partner_id.id
            })
        if not self.partner_id.property_stock_supplier.id:
            raise UserError(_("You must set a Vendor Location for this partner %s") % self.partner_id.name)
        return {
            'picking_type_id': self.picking_type_id.id,
            'partner_id': self.partner_id.id,
            'user_id': False,
            'date': self.date_order,
            'origin': self.name,
            'location_dest_id': self._get_destination_location(),
            'location_id': self.partner_id.property_stock_supplier.id,
            'company_id': self.company_id.id,
            'branch_id': self.branch_id.id
        }
