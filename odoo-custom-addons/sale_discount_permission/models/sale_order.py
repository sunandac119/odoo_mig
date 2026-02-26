from odoo import models, fields

class SaleOrder(models.Model):
    _inherit = 'sale.order'

    can_edit_discount = fields.Boolean(
        string="Can Edit Discount",
        compute="_compute_can_edit_discount"
    )

    def _compute_can_edit_discount(self):
        for record in self:
            record.can_edit_discount = self.env.user.has_group('sale_discount_permission.group_edit_sale_discount')
