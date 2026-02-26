from odoo import models, _
from odoo.exceptions import UserError
from odoo.osv import expression


class SaleOrder(models.Model):
    _inherit = "sale.order"

    def action_view_products(self):
        if not self.partner_id:
            raise UserError(_('A customer should be set on the sale order.'))

        self = self.with_company(self.company_id)

        domain = [
            ('sale_ok', '=', True),
            '&',('invoice_policy', '=', 'delivery'), ('service_type', '=', 'manual'),
            '|', ('company_id', '=', self.company_id.id), ('company_id', '=', False)]
        deposit_product = self.env['ir.config_parameter'].sudo().get_param('sale.default_deposit_product_id')
        if deposit_product:
            domain = expression.AND([domain, [('id', '!=', deposit_product)]])

        kanban_view = self.env.ref('add_product_sale_order.view_product_product_kanban_material')
        search_view = self.env.ref('add_product_sale_order.product_search_form_view_inherit_knk')
        return {
            'type': 'ir.actions.act_window',
            'name': _('Choose Products'),
            'res_model': 'product.product',
            'views': [(kanban_view.id, 'kanban'), (False, 'form')],
            'search_view_id': [search_view.id, 'search'],
            'domain': domain,
            'context': {
                # 'fsm_mode': True,
                'create': self.env['product.template'].check_access_rights('create', raise_exception=False),
                'sale_order_id': self.id,  # avoid 'default_' context key as we are going to create SOL with this context
                'pricelist': self.partner_id.property_product_pricelist.id,
                'hide_qty_buttons': self.state == 'done',
                'default_invoice_policy': 'delivery',
            },
            'help': _("""<p class="o_view_nocontent_smiling_face">
                            Create a new product
                        </p><p>
                            You must define a product for everything you sell or purchase,
                            whether it's a storable product, a consumable or a service.
                        </p>""")
        }
