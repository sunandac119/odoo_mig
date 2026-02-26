from odoo import models, api, fields, _
from odoo.exceptions import ValidationError
import xlsxwriter
import base64
from datetime import timedelta
from odoo.tools.misc import formatLang

class WizardInventoryValuationQty(models.TransientModel):
    _inherit = 'wizard.inventory.valuation.qty'

    show_product_zone = fields.Boolean(
        default=lambda self: self.env.context.get('show_product_zone', False)
    )
    zone = fields.Char(string="Zone", help="It will filter products whose display location name starts with the entered zone.")

    @api.onchange('zone')
    def _onchange_zone(self):
        self.product_ids = [(5, 0, 0)]

        key = (self.zone or '').strip()
        if not key:
            return

        # User types "A" → match "DC01-A", "DC02-A1", etc.
        pattern = f"%-{key}%"

        products = self.env['product.product'].search([
            ('type', '=', 'product'),
            ('product_tmpl_id.x_studio_display_location', '!=', False),
            ('product_tmpl_id.x_studio_display_location', 'ilike', pattern),
        ])

        self.product_ids = [(6, 0, products.ids)]

