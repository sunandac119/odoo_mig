from odoo import models, fields, api
import logging
from odoo.exceptions import UserError
import re

_logger = logging.getLogger(__name__)


class MrpBom(models.Model):
    _inherit = 'mrp.bom'

    x_scanned_barcode = fields.Char(string="Barcode")
    _barcode_uom_id = fields.Many2one('uom.uom', string="Barcode UOM", store=False)

    @api.onchange('x_scanned_barcode')
    def _onchange_x_scanned_barcode(self):
        if not self.x_scanned_barcode:
            self._barcode_uom_id = False
            return

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
            else:
                self._barcode_uom_id = False

        elif len(self.x_scanned_barcode.strip()) <= 5:
            _logger.info("=== TRYING INTERNAL REFERENCE SEARCH ===")
            product = self.env['product.product'].search([
                ('default_code', '=', self.x_scanned_barcode)
            ], limit=1)
            if product:
                self.product_tmpl_id = product.product_tmpl_id.id
                self.product_uom_id = product.uom_id.id
                self.product_qty = 0.0
            else:
                _logger.warning("=== NO PRODUCT FOUND FOR INTERNAL REFERENCE ===")
        else:
            self._barcode_uom_id = False

        if self.product_tmpl_id:
            allowed_uoms = self.product_tmpl_id.barcode_uom_ids.mapped('uom_id').ids
            return {'domain': {'product_uom_id': [('id', 'in', allowed_uoms)]}}

    @api.onchange('product_tmpl_id', 'product_qty')
    def onchange_product_id(self):
        if self.x_scanned_barcode and self._barcode_uom_id:
            self.product_uom_id = self._barcode_uom_id.id
        # elif self.product_tmpl_id:
        #     self.product_uom_id = self.product_tmpl_id.uom_id.id

        # if self.env.context.get('skip_uom_logic'):
        #     return

        # if self.product_tmpl_id and self.product_qty:
        #     all_uoms = self.product_tmpl_id.barcode_uom_ids.mapped('uom_id')
        #     qty_entered = self.product_qty
        #     match_found = False

        #     barcode_line = None
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
        #                 self = self.with_context(skip_uom_logic=True)
        #                 self.product_qty = 1
        #                 match_found = True
        #                 break

            # if not match_found and barcode_line and qty_entered != 1:
            #     _logger.info(f"=== NO MATCH, FALLBACK TO BARCODE UOM: {barcode_line.uom_id.name} ===")
            #     self.product_uom_id = barcode_line.uom_id.id

    @api.onchange('product_tmpl_id')
    def onchange_product_tmpl_id(self):
        if self.x_scanned_barcode and self._barcode_uom_id and self.product_tmpl_id:
            self.product_uom_id = self._barcode_uom_id.id
            if self.product_id.product_tmpl_id != self.product_tmpl_id:
                self.product_id = False
            for line in self.bom_line_ids:
                line.bom_product_template_attribute_value_ids = False

    @api.onchange('product_uom_id')
    def onchange_product_uom_id(self):
        barcode_line = self.env['product.barcode.uom'].search([
            ('product_id', '=', self.product_id.product_tmpl_id.id),
            ('uom_id', '=', self.product_uom_id.id)
        ], limit=1)

        if barcode_line:
            self.x_scanned_barcode = barcode_line.barcode
            
        if self.x_scanned_barcode and self._barcode_uom_id:
            if self.product_uom_id != self._barcode_uom_id:
                self.product_uom_id = self._barcode_uom_id.id

    @api.model
    def _bom_find_domain(self, product_tmpl=None, product=None, picking_type=None, company_id=False, bom_type=False):
        if product:
            if not product_tmpl:
                product_tmpl = product.product_tmpl_id
            domain = [
                '|', ('product_id', '=', product.id),
                '&', ('product_id', '=', False), ('product_tmpl_id', '=', product_tmpl.id)
            ]
        elif product_tmpl:
            domain = [('product_tmpl_id', '=', product_tmpl.id)]
        else:
            raise UserError(_('You should provide either a product or a product template to search a BoM'))

        if picking_type:
            domain += ['|', ('picking_type_id', '=', picking_type.id), ('picking_type_id', '=', False)]
        if company_id or self.env.context.get('company_id'):
            domain += ['|', ('company_id', '=', False), ('company_id', '=', company_id or self.env.context.get('company_id'))]
        if bom_type:
            domain += [('type', '=', bom_type)]
        if self._context.get('uom_id'):
            domain += [('product_uom_id', '=', int(self._context.get('uom_id')))]

        return domain

    @api.model
    def _bom_find(self, product_tmpl=None, product=None, picking_type=None, company_id=False, bom_type=False):
        if (product and product.type == 'service') or (product_tmpl and product_tmpl.type == 'service'):
            return self.env['mrp.bom']

        if self._context.get('from_scan'):
            domain = self.with_context({
                'from_scan': True,
                'uom_id': self._context.get('uom_id')
            })._bom_find_domain(
                product_tmpl=product_tmpl,
                product=product,
                picking_type=picking_type,
                company_id=company_id,
                bom_type=bom_type
            )
        else:
            domain = self._bom_find_domain(
                product_tmpl=product_tmpl,
                product=product,
                picking_type=picking_type,
                company_id=company_id,
                bom_type=bom_type
            )

        if not domain:
            return self.env['mrp.bom']

        return self.search(domain, order='sequence, product_id', limit=1)


class MrpBomLine(models.Model):
    _inherit = 'mrp.bom.line'

    x_scanned_barcode = fields.Char(string="Barcode")
    _barcode_uom_id = fields.Many2one('uom.uom', string="Barcode UOM", store=False)
    name = fields.Char(string="Description")

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
        self.name = f"{product_name} X {uom_name}" if 'UNIT' not in uom_name.upper() else product_name

    @api.onchange('x_scanned_barcode')
    def _onchange_x_scanned_barcode(self):
        if not self.x_scanned_barcode:
            self._barcode_uom_id = False
            return

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
            else:
                self._barcode_uom_id = False

        elif len(self.x_scanned_barcode.strip()) <= 5:
            _logger.info("=== TRYING INTERNAL REFERENCE SEARCH ===")
            product = self.env['product.product'].search([
                ('default_code', '=', self.x_scanned_barcode)
            ], limit=1)
            if product:
                self.product_id = product.id
                self.product_uom_id = product.uom_id.id
                self.product_qty = 0.0
            else:
                _logger.warning("=== NO PRODUCT FOUND FOR INTERNAL REFERENCE ===")
        else:
            self._barcode_uom_id = False

        if 'UNIT' not in (self.product_uom_id.name or '').upper():
            self.name = barcode_line.description or f"{self.product_id.name} X {barcode_line.uom_id.name}"
        else:
            self.name = barcode_line.description or self.product_id.name

        if self.product_id:
            allowed_uoms = self.product_id.barcode_uom_ids.mapped('uom_id').ids
            return {'domain': {'product_uom_id': [('id', 'in', allowed_uoms)]}}

    @api.onchange('product_id', 'product_qty')
    def onchange_product_id(self):
        if self.x_scanned_barcode and self._barcode_uom_id:
            self.product_uom_id = self._barcode_uom_id.id
            return
        # elif self.product_id:
        #     self.product_uom_id = self.product_id.uom_id.id

        # if self.env.context.get('skip_uom_logic'):
        #     return

        # if self.product_id and self.product_qty:
        #     all_uoms = self.product_id.barcode_uom_ids.mapped('uom_id')
        #     qty_entered = self.product_qty
        #     match_found = False

        #     barcode_line = None
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
        #                 self = self.with_context(skip_uom_logic=True)
        #                 self.product_qty = 1
        #                 match_found = True
        #                 break

            # if not match_found and barcode_line and qty_entered != 1:
            #     _logger.info(f"=== NO MATCH, FALLBACK TO BARCODE UOM: {barcode_line.uom_id.name} ===")
            #     self.product_uom_id = barcode_line.uom_id.id

    @api.onchange('product_uom_id')
    def onchange_product_uom_id(self):
        if self.x_scanned_barcode and self._barcode_uom_id:
            if self.product_uom_id != self._barcode_uom_id:
                self.product_uom_id = self._barcode_uom_id.id
