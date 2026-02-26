# -*- coding: utf-8 -*-
from odoo import api, models

class EventPosBrandReport(models.AbstractModel):
    _name = 'report.event_pos_brand_report_v2.report_pdf'
    _description = 'Event POS Brand PDF Report (Team + CTN)'

    @api.model
    def _get_report_values(self, docids, data=None):
        wizard = self.env['event.pos.brand.wizard'].browse(docids[:1])
        brand_field = data.get('brand_field')
        show_ctn = data.get('show_ctn_qty', True)
        sold_brand_ids = data.get('sold_brand_ids', [])

        pt_model = self.env['product.template']
        field = pt_model._fields.get(brand_field)
        BrandModel = self.env[field.comodel_name] if field and field.type == 'many2one' else self.env['product.brand']

        brands = BrandModel.browse(sold_brand_ids).sorted(key=lambda b: (b.name or '').lower())

        brand_pages = []
        for b in brands:
            # All active product templates for this brand
            products = pt_model.search([(brand_field, '=', b.id), ('active', '=', True)]).sorted(key=lambda p: (p.name or '').lower())
            rows = []
            for p in products:
                # find a barcode to print
                bc = ''
                if p.product_variant_ids:
                    bc = p.product_variant_ids[:1].barcode or ''
                if not bc and 'barcode' in p._fields:
                    bc = p.barcode or ''

                row = {
                    'name': p.name,
                    'default_code': p.default_code or '',
                    'barcode': bc or '',
                    'uom': p.uom_id.name or '',
                    'list_price': p.list_price,
                }
                if show_ctn:
                    row['ctn_qty'] = getattr(p, 'ctn_qty', False) if 'ctn_qty' in p._fields else False
                rows.append(row)

            brand_pages.append({'brand_name': b.name or '—', 'products': rows})

        return {
            'doc_ids': wizard.ids,
            'doc_model': 'event.pos.brand.wizard',
            'wizard': wizard,
            'day_str': data.get('day_str'),
            'sales_team_name': data.get('sales_team_name'),
            'show_ctn_qty': show_ctn,
            'brand_pages': brand_pages,
        }
