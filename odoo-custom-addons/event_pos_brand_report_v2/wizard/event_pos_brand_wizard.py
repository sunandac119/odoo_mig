# -*- coding: utf-8 -*-
from odoo import api, fields, models, _
from odoo.exceptions import UserError
from datetime import datetime, date, time, timedelta
import pytz

class EventPosBrandWizard(models.TransientModel):
    _name = 'event.pos.brand.wizard'
    _description = 'Event POS Brand Report Wizard'

    sales_team_id = fields.Many2one('crm.team', string='Sales Team', required=True)
    show_ctn_qty = fields.Boolean(string='Show CTN Qty column', default=True)

    # --- helpers ---
    def _brand_field_name(self):
        """Return the name of the Many2one brand field on product.template, or None."""
        pt = self.env['product.template']
        candidates = ['brand_id', 'product_brand_id', 'x_brand_id', 'x_studio_brand_id']
        for fname in candidates:
            if fname in pt._fields and getattr(pt._fields[fname], 'type', None) == 'many2one':
                return fname
        return None

    def _yesterday_bounds_utc(self):
        # Compute yesterday in user's timezone, then convert to UTC start/end
        user_tz = self.env.user.tz or 'UTC'
        tz = pytz.timezone(user_tz)
        today_local = datetime.now(tz).date()
        yday = today_local - timedelta(days=1)
        start_local = tz.localize(datetime.combine(yday, time.min))
        end_local = tz.localize(datetime.combine(yday, time.max).replace(microsecond=0))
        return yday.strftime('%Y-%m-%d'), start_local.astimezone(pytz.UTC), end_local.astimezone(pytz.UTC)

    def _get_report_filename(self):
        self.ensure_one()
        day_str, _, _ = self._yesterday_bounds_utc()
        parts = ['Event_POS_Brand_By_Team', day_str, self.sales_team_id.name.replace(' ', '_')]
        return '_'.join(parts)

    # --- action ---
    def action_print_pdf(self):
        self.ensure_one()
        brand_field = self._brand_field_name()
        if not brand_field:
            raise UserError(_('No brand field found on product.template. Install product_brand or add a brand field.'))

        day_str, start_utc, end_utc = self._yesterday_bounds_utc()

        # POS Orders for yesterday, filtered by the POS Config's Sales Team
        domain = [
            ('state', 'in', ['paid', 'done', 'invoiced']),
            ('date_order', '>=', fields.Datetime.to_string(start_utc)),
            ('date_order', '<=', fields.Datetime.to_string(end_utc)),
            ('session_id.config_id.crm_team_id', '=', self.sales_team_id.id),
        ]

        orders = self.env['pos.order'].search(domain)
        if not orders:
            raise UserError(_('No POS orders found for yesterday for the selected Sales Team.'))

        lines = orders.mapped('lines')
        if not lines:
            raise UserError(_('No POS order lines found.'))

        # Collect brands sold yesterday
        sold_brand_ids = set()
        for l in lines:
            tmpl = l.product_id.product_tmpl_id
            brand = getattr(tmpl, brand_field, False)
            if brand:
                sold_brand_ids.add(brand.id)

        if not sold_brand_ids:
            raise UserError(_('No Brands detected in sold items for yesterday.'))

        data = {
            'day_str': day_str,
            'sales_team_name': self.sales_team_id.name,
            'brand_field': brand_field,
            'show_ctn_qty': self.show_ctn_qty,
            'sold_brand_ids': list(sold_brand_ids),
        }
        return self.env.ref('event_pos_brand_report_v2.action_event_pos_brand_report').report_action(self, data=data, config=False)
