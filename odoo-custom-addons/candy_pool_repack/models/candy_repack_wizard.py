# -*- coding: utf-8 -*-
from odoo import models, fields, api, _
from odoo.exceptions import ValidationError
import logging

_logger = logging.getLogger(__name__)


class CandyRepackWizard(models.TransientModel):
    _name = 'candy.repack.wizard'
    _description = 'Candy Pool Repacking Wizard'

    # Scan input
    scan_barcode = fields.Char(string="Scan Barcode")

    # Locations
    location_id = fields.Many2one(
        'stock.location',
        string="Source Location",
        required=True,
        domain=[('usage', '=', 'internal')],
    )

    dest_location_id = fields.Many2one(
        'stock.location',
        string="Destination Location (Pool)",
        required=True,
        domain=[('usage', '=', 'internal')],
    )

    repack_location_id = fields.Many2one(
        'stock.location',
        string="Repack Virtual Location",
        required=True,
        domain=[('usage', 'in', ('inventory', 'production'))],
        default=lambda self: self.env.ref('candy_pool_repack.stock_location_candy_repack', raise_if_not_found=False),
        help="Virtual location used to convert packs into bulk pool without needing a fixed BOM.",
    )

    pool_product_id = fields.Many2one(
        'product.product',
        string="Candy Pool Product (Sold by Weight)",
        required=True,
        help="This product must use a Weight UoM category (e.g., kg).",
    )

    line_ids = fields.One2many('candy.repack.line', 'wizard_id', string="Candy Packs")

    company_id = fields.Many2one('res.company', default=lambda self: self.env.company, required=True)
    currency_id = fields.Many2one('res.currency', related='company_id.currency_id', readonly=True)

    total_weight_kg = fields.Float(string="Total Weight (kg)", compute="_compute_totals", store=False, digits=(16, 4))
    total_cost = fields.Monetary(string="Total Cost", compute="_compute_totals", store=False)
    cost_per_kg = fields.Monetary(string="Cost per kg", compute="_compute_totals", store=False)

    @api.onchange('location_id')
    def _onchange_location_id(self):
        if self.location_id and not self.dest_location_id:
            self.dest_location_id = self.location_id.id

    @api.depends('line_ids.qty', 'line_ids.product_id')
    def _compute_totals(self):
        for wiz in self:
            total_w = 0.0
            total_c = 0.0
            for line in wiz.line_ids:
                if not line.product_id:
                    continue
                # product.weight is stored in kg in standard Odoo
                total_w += (line.product_id.weight or 0.0) * (line.qty or 0.0)

                # standard_price is per product.uom_id (usually Unit for packs)
                total_c += (line.product_id.standard_price or 0.0) * (line.qty or 0.0)

            wiz.total_weight_kg = total_w
            wiz.total_cost = total_c
            wiz.cost_per_kg = (total_c / total_w) if total_w else 0.0

    # -------------------------
    # Barcode scan handling
    # -------------------------
    @api.onchange('scan_barcode')
    def _onchange_scan_barcode(self):
        if not self.scan_barcode:
            return

        barcode = (self.scan_barcode or '').strip()
        self.scan_barcode = ''  # clear after scan

        product = self._barcode_to_product(barcode)
        if not product:
            raise ValidationError(_("Barcode not found: %s") % barcode)

        if not product.weight or product.weight <= 0:
            raise ValidationError(_("Product %s has no Weight set. Please set Weight (kg) in Inventory tab.") % product.display_name)

        # Add or increment line by 1 pack per scan
        existing = self.line_ids.filtered(lambda l: l.product_id.id == product.id)[:1]
        if existing:
            existing.qty += 1
        else:
            self.line_ids = [(0, 0, {'product_id': product.id, 'qty': 1.0})]

    def _barcode_to_product(self, barcode):
        '''Resolve barcode into a product.product. Supports your product.barcode.uom model and standard barcode/default_code.'''
        BarcodeUom = self.env['product.barcode.uom']

        # 1) Custom UoM barcode mapping (template)
        line = BarcodeUom.search([('barcode', '=', barcode)], limit=1)
        if line:
            tmpl = line.product_id
            product = tmpl.product_variant_id or tmpl.product_variant_ids[:1]
            return product

        # 2) Standard barcode
        product = self.env['product.product'].search([('barcode', '=', barcode)], limit=1)
        if product:
            return product

        # 3) Internal reference
        return self.env['product.product'].search([('default_code', '=', barcode)], limit=1)

    # -------------------------
    # Confirm repack (creates a conversion picking)
    # -------------------------
    def action_confirm(self):
        self.ensure_one()

        if not self.line_ids:
            raise ValidationError(_("Please scan/add at least one candy pack."))

        if self.total_weight_kg <= 0:
            raise ValidationError(_("Total weight is zero. Ensure products have Weight (kg) and quantity > 0."))

        if not self.location_id or not self.dest_location_id or not self.repack_location_id:
            raise ValidationError(_("Please set Source, Destination, and Repack virtual locations."))

        # Update pool product standard_price to computed cost/kg so valuation of receipt matches your pool cost.
        if self.cost_per_kg > 0:
            self.pool_product_id.standard_price = self.cost_per_kg

        picking_type = self._get_internal_picking_type()

        picking = self.env['stock.picking'].create({
            'picking_type_id': picking_type.id,
            'location_id': self.location_id.id,
            'location_dest_id': self.dest_location_id.id,
            'origin': _('Candy Pool Repack'),
            'company_id': self.company_id.id,
        })

        # Consume packs: source -> virtual repack location
        for line in self.line_ids:
            if line.qty <= 0:
                continue
            self.env['stock.move'].create({
                'name': line.product_id.display_name,
                'product_id': line.product_id.id,
                'product_uom_qty': line.qty,
                'product_uom': line.product_id.uom_id.id,
                'picking_id': picking.id,
                'location_id': self.location_id.id,
                'location_dest_id': self.repack_location_id.id,
                'company_id': self.company_id.id,
            })

        # Produce pool: virtual repack location -> destination
        self.env['stock.move'].create({
            'name': self.pool_product_id.display_name,
            'product_id': self.pool_product_id.id,
            'product_uom_qty': self.total_weight_kg,
            'product_uom': self.pool_product_id.uom_id.id,
            'picking_id': picking.id,
            'location_id': self.repack_location_id.id,
            'location_dest_id': self.dest_location_id.id,
            'company_id': self.company_id.id,
        })

        picking.action_confirm()
        picking.action_assign()
        picking.button_validate()

        return {
            'type': 'ir.actions.act_window',
            'res_model': 'stock.picking',
            'view_mode': 'form',
            'res_id': picking.id,
        }

    def _get_internal_picking_type(self):
        picking_type = self.env['stock.picking.type'].search([
            ('code', '=', 'internal'),
            ('warehouse_id.company_id', '=', self.company_id.id),
        ], limit=1)
        if not picking_type:
            picking_type = self.env['stock.picking.type'].search([('code', '=', 'internal')], limit=1)
        if not picking_type:
            raise ValidationError(_("Internal picking type not found. Ensure Inventory app is configured."))
        return picking_type


class CandyRepackLine(models.TransientModel):
    _name = 'candy.repack.line'
    _description = 'Candy Pool Repack Line'

    wizard_id = fields.Many2one('candy.repack.wizard', required=True, ondelete='cascade')
    product_id = fields.Many2one('product.product', string="Candy Pack", required=True)
    qty = fields.Float(string="Qty (Pack)", default=1.0)

    weight_kg = fields.Float(string="Weight (kg)", compute="_compute_line", store=False, digits=(16, 4))
    line_cost = fields.Float(string="Line Cost", compute="_compute_line", store=False, digits=(16, 2))

    @api.depends('product_id', 'qty')
    def _compute_line(self):
        for line in self:
            line.weight_kg = (line.product_id.weight or 0.0) * (line.qty or 0.0)
            line.line_cost = (line.product_id.standard_price or 0.0) * (line.qty or 0.0)
