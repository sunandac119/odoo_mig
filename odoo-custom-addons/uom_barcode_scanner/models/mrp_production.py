from odoo import models, fields, api
import logging
import re
from odoo.exceptions import ValidationError

_logger = logging.getLogger(__name__)


class MrpProduction(models.Model):
    _inherit = 'mrp.production'

    x_scanned_barcode = fields.Char(string="Barcode")
    _barcode_uom_id = fields.Many2one('uom.uom', string="Barcode UOM", store=False)

    # ========== Onchange: Barcode ==========
    @api.onchange('x_scanned_barcode')
    def _onchange_x_scanned_barcode(self):
        if not self.x_scanned_barcode:
            self._barcode_uom_id = False
            return

        # Try matching product.barcode.uom
        barcode_line = self.env['product.barcode.uom'].search([
            ('barcode', '=', self.x_scanned_barcode)
        ], limit=1)

        if barcode_line:
            self.product_tmpl_id = barcode_line.product_id.id
            product = self.env['product.product'].search([
                ('product_tmpl_id', '=', barcode_line.product_id.id)
            ], limit=1)

            if product:
                self._barcode_uom_id = barcode_line.uom_id.id
                self.product_id = product.id
                self.product_uom_id = barcode_line.uom_id.id
                self.product_qty = 0.0
                # if not self.product_qty:
                #     self.product_qty = 0.0
            else:
                self._barcode_uom_id = False

        # Fallback: Internal reference (short codes)
        elif len(self.x_scanned_barcode.strip()) <= 5:
            _logger.info("=== TRYING INTERNAL REFERENCE SEARCH ===")
            product = self.env['product.product'].search([
                ('default_code', '=', self.x_scanned_barcode)
            ], limit=1)
            if product:
                self.product_qty = 0.0
                self.product_id = product.id
                self.product_uom_id = product.uom_id.id
            else:
                _logger.warning("=== NO PRODUCT FOUND FOR INTERNAL REFERENCE ===")

        else:
            self._barcode_uom_id = False

        # Restrict UoM domain
        if self.product_id:
            allowed_uoms = self.product_id.barcode_uom_ids.mapped('uom_id').ids
            return {'domain': {'product_uom_id': [('id', 'in', allowed_uoms)]}}


    # ========== Onchange: UoM / Qty ==========
    @api.onchange('product_uom_id', 'product_qty')
    def onchange_uom(self):
        barcode_line = self.env['product.barcode.uom'].search([
            ('product_id', '=', self.product_id.product_tmpl_id.id),
            ('uom_id', '=', self.product_uom_id.id)
        ], limit=1)

        if barcode_line:
            self.x_scanned_barcode = barcode_line.barcode
            
        product_name = self.product_id.name or ''
        uom_name = self.product_uom_id.name or ''


        # if 'UNIT' not in uom_name.upper() and product_name and uom_name:
        #     self.name = f"{product_name} X {uom_name}"
        # else:
        #     self.name = product_name or "New"
        # print("\n\n\n\n\n\n\n=========canlll uom",self.name)

    # ========== Onchange: Product ==========
    @api.onchange('product_id', 'picking_type_id', 'company_id')
    def onchange_product_id(self):
        picking_type_id = self._context.get('default_picking_type_id')
        picking_type = picking_type_id and self.env['stock.picking.type'].browse(picking_type_id)

        if self.x_scanned_barcode and self._barcode_uom_id:
            self.product_uom_id = self._barcode_uom_id.id

            if not self.product_id:
                self.bom_id = False
            elif not self.bom_id or self.bom_id.product_tmpl_id != self.product_tmpl_id or (self.bom_id.product_id and self.bom_id.product_id != self.product_id):
                bom = self.env['mrp.bom'].with_context({
                    'from_scan': True,
                    'uom_id': self.product_uom_id
                })._bom_find(product=self.product_id, picking_type=picking_type, company_id=self.company_id.id, bom_type='normal')

                if bom:
                    self.bom_id = bom.id
                    self.product_qty = self.bom_id.product_qty
                    self.product_uom_id = self.bom_id.product_uom_id.id
                else:
                    self.bom_id = False
                return

        else:
            if not self.product_id:
                self.bom_id = False
            elif not self.bom_id or self.bom_id.product_tmpl_id != self.product_tmpl_id or (self.bom_id.product_id and self.bom_id.product_id != self.product_id):
                bom = self.env['mrp.bom']._bom_find(product=self.product_id, picking_type=picking_type, company_id=self.company_id.id, bom_type='normal')

                if bom:
                    self.bom_id = bom.id
                    self.product_qty = self.bom_id.product_qty
                    self.product_uom_id = self.bom_id.product_uom_id.id
                else:
                    self.bom_id = False
                    self.product_uom_id = self.product_id.uom_id.id

    # ========== Onchange: BOM ==========
    @api.onchange('bom_id')
    def _onchange_bom_id(self):
        picking_type_id = self._context.get('default_picking_type_id')
        picking_type = picking_type_id and self.env['stock.picking.type'].browse(picking_type_id)

        if self.x_scanned_barcode and self._barcode_uom_id:
            if not self.product_id and self.bom_id:
                self.product_id = self.bom_id.product_id or self.bom_id.product_tmpl_id.product_variant_ids[:1]

            self.product_qty = self.bom_id.product_qty or 1.0
            self.product_uom_id = self._barcode_uom_id

        else:
            if not self.product_id and self.bom_id:
                self.product_id = self.bom_id.product_id or self.bom_id.product_tmpl_id.product_variant_ids[:1]

            self.product_qty = self.bom_id.product_qty or 1.0
            self.product_uom_id = self.bom_id.product_uom_id.id if self.bom_id else self.product_id.uom_id.id

        # Clean moves
        self.move_raw_ids = [(2, move.id) for move in self.move_raw_ids.filtered(lambda m: m.bom_line_id)]
        self.move_finished_ids = [(2, move.id) for move in self.move_finished_ids]
        self.picking_type_id = picking_type or (self.bom_id and self.bom_id.picking_type_id) or self.picking_type_id

    # ========== Onchange: Qty / UoM ==========
    @api.onchange('product_qty', 'product_uom_id')
    def onchange_product_uom_id(self):
        """Override UOM change to preserve barcode UOM"""
        if self.x_scanned_barcode and self._barcode_uom_id:
            if self.product_uom_id != self._barcode_uom_id:
                self.product_uom_id = self._barcode_uom_id.id
            return

        # Sync workorders
        for workorder in self.workorder_ids:
            workorder.product_uom_id = self.product_uom_id
            if self._origin.product_qty:
                ratio = self.product_qty / self._origin.product_qty
                workorder.duration_expected = workorder._get_duration_expected(ratio=ratio)
            else:
                workorder.duration_expected = workorder._get_duration_expected()

            if workorder.date_planned_start and workorder.duration_expected:
                workorder.date_planned_finished = workorder.date_planned_start + relativedelta(minutes=workorder.duration_expected)

        # ======= DYNAMIC QTY-BASED UOM SELECTION =======
        # if self.env.context.get('skip_uom_logic'):
        #     return  # Skip matching & fallback if qty=1 was auto-set

        # if self.product_id and self.product_qty:
        #     qty_entered = self.product_qty
        #     all_uoms = self.product_id.barcode_uom_ids.mapped('uom_id')
        #     match_found, barcode_line = False, None

        #     if self.x_scanned_barcode:
        #         barcode_line = self.env['product.barcode.uom'].search([
        #             ('barcode', '=', self.x_scanned_barcode)
        #         ], limit=1)

        #     for uom in all_uoms:
        #         match = re.search(r'\d+', uom.name)
        #         if match:
        #             multiplier = int(match.group(0))
        #             _logger.info(f"UOM Name: {uom.name} → Multiplier: {multiplier}")

        #             if multiplier == int(qty_entered):
        #                 _logger.info(f"=== MATCH FOUND: QTY={qty_entered}, UOM={uom.name} ===")
        #                 self.product_uom_id = uom.id

        #                 # Prevent recursion when setting qty=1
        #                 self = self.with_context(skip_uom_logic=True)
        #                 self.product_qty = 1
        #                 match_found = True
        #                 break

            # Fallback: Use barcode UoM if no match and qty≠1
            # if not match_found and barcode_line and qty_entered != 1:
            #     _logger.info(f"=== NO MATCH, FALLBACK TO BARCODE UOM: {barcode_line.uom_id.name} ===")
            #     self.product_uom_id = barcode_line.uom_id.id
    
    #===============UOM QTY UPDATE======================
    @api.onchange('x_scanned_barcode', 'move_raw_ids')
    def _onchange_x_scanned_barcode_move_raw_ids(self):
        if not self.x_scanned_barcode:
            return

        bom_id = self.env['mrp.bom'].search([
            ('x_scanned_barcode', '=', self.x_scanned_barcode)
        ], limit=1)

        if self.product_id and self.product_id.is_weight:
            move_lines = self.move_raw_ids
            bom_lines = bom_id.bom_line_ids if bom_id else self.env['mrp.bom.line']

            for idx, line in enumerate(move_lines):
                if bom_id and idx < len(bom_lines):
                    bom_line = bom_lines[idx]
                    qty = bom_line.product_qty

                    product = self.env['product.product'].search([
                        ('barcode', '=', bom_line.x_scanned_barcode)
                    ], limit=1)
                else:
                    product = line.product_id
                    qty = line.product_uom_qty or 1.0

                kg_uom = self.env['uom.uom'].search([
                    ('name', '=', 'KG'),
                    ('category_id', '=', product.uom_id.category_id.id)
                ], limit=1)

                if not kg_uom:
                    kg_uom = self.env['uom.uom'].create({
                        'name': 'KG',
                        'category_id': product.uom_id.category_id.id,
                        'factor_inv': 1.0,
                        'uom_type': 'bigger'
                    })

                line.product_uom = kg_uom.id
                line.x_scanned_barcode = product.barcode
                line.name = product.name

                if bom_id and idx < len(bom_lines):
                    weight = product.weight
                    if qty and weight:
                        line.product_uom_qty = qty * weight

            self.product_qty = sum(line.product_uom_qty for line in self.move_raw_ids)
            
        else:
            move_lines = self.move_raw_ids
            bom_lines = bom_id.bom_line_ids if bom_id else self.env['mrp.bom.line']
            for idx, line in enumerate(move_lines):
                if idx < len(bom_lines):
                    bom_line = bom_lines[idx]
                    product = self.env['product.product'].search([
                        ('barcode', '=', bom_line.x_scanned_barcode)
                    ], limit=1)

                    line.x_scanned_barcode = bom_line.x_scanned_barcode
                    line.name = product.name
                    line.product_uom_qty = bom_line.product_qty

    def print_barcode(self):
        return self.env.ref('uom_barcode_scanner.print_barcode_report').report_action(self)
