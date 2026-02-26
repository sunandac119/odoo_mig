# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.


from odoo import _, api, fields, models
from odoo.exceptions import UserError
from collections import defaultdict
from odoo.tools import misc


class ProductLabelLayout(models.TransientModel):
    _name = 'product.label.layout'
    _description = 'Choose the sheet layout to print the labels'

    print_format = fields.Selection([
        ('dymo', 'Dymo'),
        ('2x7xprice', '2 x 7 with price'),
        ('4x7xprice', '4 x 7 with price'),
        ('4x12', '4 x 12'),
        ('4x12xprice', '4 x 12 with price'),
        ('zpl', 'ZPL Labels'),
        ('zplxprice', 'ZPL Labels with price')
    ], string="Format", default='dymo', required=True)
        # ondelete={'zpl': 'set default', 'zplxprice': 'set default'})
    custom_quantity = fields.Integer('Quantity', default=1, required=True)
    product_ids = fields.Many2many('product.product')
    product_tmpl_ids = fields.Many2many('product.template')
    extra_html = fields.Html('Extra Content', default='')
    rows = fields.Integer(compute='_compute_dimensions')
    columns = fields.Integer(compute='_compute_dimensions')

    move_line_ids = fields.Many2many('stock.move.line')
    picking_quantity = fields.Selection([
        ('picking', 'Transfer Quantities'),
        ('custom', 'Custom')], string="Quantity to print",
        required=True, default='custom')

    @api.depends('print_format')
    def _compute_dimensions(self):
        for wizard in self:
            if 'x' in wizard.print_format:
                columns, rows = wizard.print_format.split('x')[:2]
                wizard.columns = int(columns)
                wizard.rows = int(rows)
            else:
                wizard.columns, wizard.rows = 1, 1

    def _prepare_report_data(self):
        if self.custom_quantity <= 0:
            raise UserError(_('You need to set a positive quantity.'))

        # Get layout grid
        if self.print_format == 'dymo':
            xml_id = 'bista_product_label.report_product_template_label_dymo'
        # elif 'x' in self.print_format:
        #     xml_id = 'product.report_product_template_label'
        else:
            xml_id = ''

        active_model = ''
        if self.product_tmpl_ids:
            products = self.product_tmpl_ids.ids
            active_model = 'product.template'
        elif self.product_ids:
            products = self.product_ids.ids
            active_model = 'product.product'

        # Build data to pass to the report
        data = {
            'active_model': active_model,
            'quantity_by_product': {p: self.custom_quantity for p in products},
            'layout_wizard': self.id,
            'price_included': 'xprice' in self.print_format,
        }

        # if 'zpl' in self.print_format:
        #     xml_id = 'stock.label_product_product'

        if self.picking_quantity == 'picking' and self.move_line_ids:
            qties = defaultdict(int)
            custom_barcodes = defaultdict(list)
            uom_unit = self.env.ref('uom.product_uom_categ_unit', raise_if_not_found=False)
            for line in self.move_line_ids:
                if line.product_uom_id.category_id == uom_unit:
                    if (line.lot_id or line.lot_name) and int(line.qty_done):
                        custom_barcodes[line.product_id.id].append((line.lot_id.name or line.lot_name, int(line.qty_done)))
                        continue
                    qties[line.product_id.id] += line.qty_done
            # Pass only products with some quantity done to the report
            data['quantity_by_product'] = {p: int(q) for p, q in qties.items() if q}
            data['custom_barcodes'] = custom_barcodes

        # Customized Part of Code:
        stock_production_lot = self.env['stock.production.lot']
        if bool(data['custom_barcodes']):
            prod_exp_dates = []
            for key, value in data['custom_barcodes'].items():
                prod_custom_barcodes = value
                for barcodes in prod_custom_barcodes:
                    stock_production_lot_obj = stock_production_lot.search([('name', '=', barcodes[0])])
                    barcode_exp = []
                    if "expiration_date" in stock_production_lot_obj._fields:
                        exp_date = stock_production_lot_obj.expiration_date.strftime(misc.DEFAULT_SERVER_DATE_FORMAT) if stock_production_lot_obj.expiration_date else ""
                        prod_exp_dates.append((stock_production_lot_obj.name, exp_date))
                    # prod_exp_dates.append(barcode_exp)
            data.update({"prod_exp_dates": prod_exp_dates})
            # custom_barcodes_list = data['custom_barcodes'].items()
        if "move_line_ids" in self._fields:
            picking_data = []
            for move_line in self.move_line_ids:
                # if move_line.picking_id.picking_type_id.code == 'incoming' and move_line.picking_id not in picking_data:
                if not any(d['picking_name'] == move_line.picking_id.name for d in picking_data):
                    picking_data.append({
                        'picking_name': move_line.picking_id.name,
                        'picking_type': move_line.picking_id.picking_type_id.code,
                        'partner': move_line.picking_id.partner_id.display_name,
                        'date_done': move_line.picking_id.date_done.strftime(misc.DEFAULT_SERVER_DATE_FORMAT) if move_line.picking_id.date_done else ""
                    })
            data.update({"picking_data": picking_data})

        return xml_id, data

    def process(self):
        self.ensure_one()
        xml_id, data = self._prepare_report_data()
        if not xml_id:
            raise UserError(_('Unable to find report template for %s format', self.print_format))
        return self.env.ref(xml_id).report_action(None, data=data)
