# -*- coding: utf-8 -*-
from odoo import models, fields
from collections import defaultdict
from datetime import timedelta

class PosBrand3DayByBrandWizard(models.TransientModel):
    _name = "pos.brand.3day.by.brand.wizard"
    _description = "POS 3-Day Sales by Brand (pages) Wizard"

    # Last 3 calendar days inclusive (today, -1, -2)
    date_to = fields.Datetime(required=True, default=lambda self: fields.Datetime.now())
    date_from = fields.Datetime(required=True, default=lambda self: fields.Datetime.now() - timedelta(days=2))

    team_ids = fields.Many2many('crm.team', string="Sales Teams (optional)")
    warehouse_ids = fields.Many2many('stock.warehouse', string="Warehouses (optional)")

    def _brand_name_of_template(self, tmpl):
        # Compatible with/without community product_brand
        if hasattr(tmpl, 'brand_id') and tmpl.brand_id:
            return tmpl.brand_id.name or "No Brand"
        return "No Brand"

    def _order_line_domain(self):
        domain = [
            ('order_id.date_order', '>=', self.date_from),
            ('order_id.date_order', '<=', self.date_to),
            ('order_id.state', 'in', ['paid', 'done', 'invoiced']),
        ]
        if self.warehouse_ids:
            domain.append(('order_id.config_id.picking_type_id.warehouse_id', 'in', self.warehouse_ids.ids))

        if self.team_ids:
            parts = []
            if 'team_id' in self.env['pos.order']._fields:
                parts.append(('order_id.team_id', 'in', self.team_ids.ids))
            if 'crm_team_id' in self.env['pos.config']._fields:
                parts.append(('order_id.config_id.crm_team_id', 'in', self.team_ids.ids))
            if parts:
                domain += (parts[0] if len(parts) == 1 else ['|'] + parts)
        return domain

    def _collect(self):
        """
        Returns list of brands:
        [ {'brand': 'Brand A', 'total_qty': 123.0, 'products': [{'name':..,'barcode':..,'uom':..,'qty':..}, ...]}, ... ]
        Brands sorted A→Z; products by qty DESC.
        """
        Pol = self.env['pos.order.line']
        rg = Pol.read_group(
            domain=self._order_line_domain(),
            fields=['qty:sum', 'product_id'],
            groupby=['product_id'],
            lazy=False
        )

        Product = self.env['product.product']
        prod_ids = [r['product_id'][0] for r in rg if r.get('product_id')]
        prods = Product.browse(prod_ids)
        tmpl_of = {p.id: p.product_tmpl_id for p in prods}

        # Aggregate per brand & per template
        by_brand = defaultdict(lambda: defaultdict(float))  # {brand: {tmpl_id: qty}}
        tmpl_meta = {}  # {tmpl_id: {'name':..., 'uom':..., 'barcode':...}}

        for row in rg:
            pid = row.get('product_id') and row['product_id'][0]
            if not pid:
                continue
            tmpl = tmpl_of.get(pid)
            if not tmpl:
                continue
            brand = self._brand_name_of_template(tmpl)
            qty = row.get('qty_sum') or 0.0
            by_brand[brand][tmpl.id] += qty
            # store meta once
            if tmpl.id not in tmpl_meta:
                barcode = self.env['product.product'].search([('product_tmpl_id', '=', tmpl.id)], limit=1, order='id').barcode or ''
                tmpl_meta[tmpl.id] = {
                    'name': tmpl.name,
                    'uom': tmpl.uom_id.name,
                    'barcode': barcode,
                }

        # Build output rows
        brands = []
        for brand, tmpl_qty in by_brand.items():
            products = []
            total_qty = 0.0
            for tid, q in tmpl_qty.items():
                meta = tmpl_meta.get(tid, {})
                products.append({
                    'name': meta.get('name', ''),
                    'barcode': meta.get('barcode', ''),
                    'uom': meta.get('uom', ''),
                    'qty': q,
                })
                total_qty += q
            products.sort(key=lambda x: x['qty'], reverse=True)
            brands.append({'brand': brand, 'total_qty': total_qty, 'products': products})

        # Sort brands alphabetically
        brands.sort(key=lambda x: (x['brand'] or '').lower())
        return brands

    def action_print_pdf(self):
        brands = self._collect()
        data = {
            'date_from': fields.Datetime.to_string(self.date_from),
            'date_to': fields.Datetime.to_string(self.date_to),
            'teams': ", ".join(self.team_ids.mapped('name')) if self.team_ids else '',
            'warehouses': ", ".join(self.warehouse_ids.mapped('name')) if self.warehouse_ids else '',
            'brands': brands,
        }
        return self.env.ref('pos_brand_3day_by_brand.action_report_pos_brand_3day_by_brand').report_action(self, data=data)
