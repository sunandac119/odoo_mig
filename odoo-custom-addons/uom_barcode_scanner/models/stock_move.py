from odoo import models, fields, api
import logging
from odoo.exceptions import ValidationError
import re

_logger = logging.getLogger(__name__)

class StockMove(models.Model):
    _inherit = 'stock.move'

    x_scanned_barcode = fields.Char(string="Barcode")
    _barcode_uom_id = fields.Many2one('uom.uom', string="Barcode UOM", store=False)

    # @api.model
    # def create(self, vals):
    #     res = super().create(vals)
    #     if vals.get('x_scanned_barcode'):
    #         return res
    #     elif vals.get('product_id') and vals.get('product_uom'):
    #         product_id = vals['product_id']
    #         product = self.env['product.product'].browse(product_id)
    #         barcode_line = self.env['product.barcode.uom'].search([
    #             ('barcode', '=', product.barcode),
    #             ('uom_id', '=', vals.get('product_uom')),
    #         ], limit=1)
    #         vals = {
    #             'x_scanned_barcode': barcode_line.barcode,
    #             'description_picking': barcode_line.description,
    #             'name':barcode_line.description 
    #         }
    #         res.sudo().write(vals)
    #         print('\n\n\n\n\n vals',vals)
    #         print('\n\n\n\n\n res',res)
    #     return res
    @api.model
    def create(self, vals):
        print("\n\n---------------------------------")
        """Ensure the correct product_uom and barcode are set based on carton/unit relationship."""
        
        # Skip logic if explicitly disabled
        if self.env.context.get('skip_barcode_uom'):
            return super().create(vals)

        product = None
        if vals.get('product_id'):
            product = self.env['product.product'].browse(vals['product_id'])

        # Fix wrong UoM during move creation if linked to sale_line
        if vals.get('sale_line_id') and product:
            sale_line = self.env['sale.order.line'].browse(vals['sale_line_id'])
            if sale_line.product_uom:
                vals['product_uom'] = sale_line.product_uom.id
                vals['product_uom_qty'] = sale_line.product_uom_qty

        # Fix UoM if linked via picking
        elif vals.get('picking_id') and product:
            picking = self.env['stock.picking'].browse(vals['picking_id'])
            if picking.origin:
                sale_order = self.env['sale.order'].search([('name', '=', picking.origin)], limit=1)
                if sale_order:
                    # Match move by product
                    line = sale_order.order_line.filtered(lambda l: l.product_id.id == product.id)
                    if line:
                        line = line[0]  # <-- Singleton fix: pick the first matching line
                        vals['product_uom'] = line.product_uom.id
                        vals['product_uom_qty'] = line.product_uom_qty
                        _logger.info(
                            "Matched stock.move to sale.order.line %s for product %s",
                            line.id, product.display_name
                        )

        # Call super to actually create move
        res = super().create(vals)

        # Auto-set barcode from product.barcode.uom if not already present
        if not vals.get('x_scanned_barcode') and vals.get('product_id') and vals.get('product_uom'):
            barcode_line = self.env['product.barcode.uom'].search([
                ('barcode', '=', product.barcode),
                ('uom_id', '=', vals.get('product_uom')),
            ], limit=1)
            if barcode_line:
                res.sudo().write({
                    'x_scanned_barcode': barcode_line.barcode,
                    'description_picking': barcode_line.description,
                    'name': barcode_line.description
                })

        # Auto-set quantity_done and validate picking if required
        # if vals.get('state') == 'done' and self.env.context.get('apply_barcode_uom_logic'):
        #     qty_done = vals.get('product_uom_qty')
        #     vals['quantity_done'] = qty_done
        #     print('\n\n\n\n\n\n Setting quantity_done', qty_done)
        #     write_vals = res.sudo().write({
        #         'quantity_done': qty_done,
        #         'state': 'done'
        #     })
        #     print('\n\n\n\n\n\n write_valswrite_valswrite_vals',write_vals)

        #     picking = res.picking_id.sudo()
        #     if picking:
        #         try:
        #             picking._compute_state()
        #             picking.action_assign()
        #             picking.button_validate()
        #         except Exception as e:
        #             _logger.warning(f"Failed to auto-validate picking {picking.name}: {e}")

        _logger.info("Created stock.move %s with corrected UoM %s", res.name, res.product_uom.display_name)
        test = res
        print("\n\n---------------------->",test)
        return test

    # @api.constrains('product_uom_qty')
    # def _check_product_uom_qty(self):
    #     for line in self:
    #         if line.product_uom_qty <= 0:
    #             raise ValidationError("The quantity must be greater than 0.")

    @api.onchange('x_scanned_barcode')
    def _onchange_x_scanned_barcode(self):
        if not self.x_scanned_barcode:
            self._barcode_uom_id = False
            return

        barcode_line = self.env['product.barcode.uom'].search([
            ('barcode', '=', self.x_scanned_barcode)
        ], limit=1)

        if barcode_line:
            product = self.env['product.product'].search([
                ('product_tmpl_id', '=', barcode_line.product_id.id)
            ], limit=1)

            if product:
                self._barcode_uom_id = barcode_line.uom_id.id
                self.product_id = product.id
                self.product_uom = barcode_line.uom_id.id
                self.product_uom_qty = 0.0
            else:
                self._barcode_uom_id = False

        elif len(self.x_scanned_barcode.strip()) <= 5:
            _logger.info("=== TRYING INTERNAL REFERENCE SEARCH ===")
            product = self.env['product.product'].search([
                ('default_code', '=', self.x_scanned_barcode)
            ], limit=1)

            if product:
                self.product_id = product.id
                self.product_uom = product.uom_id.id
                self.product_uom_qty = 0.0
            else:
                _logger.warning("=== NO PRODUCT FOUND FOR INTERNAL REFERENCE ===")

        else:
            self._barcode_uom_id = False
        _logger.warning("=== NO PRODUCT FOUND FOR INTERNAL REFERENCE ===")

        if 'UNIT' not in (self.product_uom.name or '').upper() and self.product_id.name and barcode_line.uom_id.name:
            self.name = barcode_line.description or f"{self.product_id.name} X {barcode_line.uom_id.name}"
        else:
            self.name = barcode_line.description or self.product_id.name or ""


        if self.product_id:
            allowed_uoms = self.product_id.barcode_uom_ids.mapped('uom_id').ids
            return {'domain': {'product_uom': [('id', 'in', allowed_uoms)]}}

    @api.onchange('product_uom', 'product_uom_qty', 'quantity_done')
    def onchange_uom(self):
        product_name = self.product_id.name or ''
        uom_name = self.product_uom.name or ''

        barcode_line = self.env['product.barcode.uom'].search([
            ('product_id', '=', self.product_id.product_tmpl_id.id),
            ('uom_id', '=', self.product_uom.id)
        ], limit=1)

        if barcode_line:
            self.x_scanned_barcode = barcode_line.barcode

        if 'UNIT' not in uom_name.upper():
            self.name = f"{product_name} X {uom_name}"
            self.description_picking = f"{product_name} X {uom_name}"
        else:
            self.name = product_name
            self.description_picking = product_name

    # @api.onchange('product_id', 'product_uom_qty', 'quantity_done')
    @api.onchange('product_id', 'product_uom_qty')
    def onchange_product_id(self):
        if self.x_scanned_barcode and self._barcode_uom_id:
            self.product_uom = self._barcode_uom_id.id
            return

        if self.product_id:
            product = self.product_id.with_context(lang=self._get_lang())

        # if self.env.context.get('skip_uom_logic'):
        #     return

        # if self.product_id and self.product_uom_qty:
        #     all_uoms = self.product_id.barcode_uom_ids.mapped('uom_id')
        #     qty_entered = self.product_uom_qty
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
        #                 self.product_uom = uom.id
        #                 self = self.with_context(skip_uom_logic=True)
        #                 self.product_uom_qty = 1
        #                 match_found = True
        #                 break

            # if not match_found and barcode_line and qty_entered != 1:
            #     _logger.info(f"=== NO MATCH, FALLBACK TO BARCODE UOM: {barcode_line.uom_id.name} ===")
            #     self.product_uom = barcode_line.uom_id.id

    @api.onchange('product_uom')
    def _onchange_product_uom(self):
        if self.x_scanned_barcode and self._barcode_uom_id:
            if self.product_uom != self._barcode_uom_id:
                self.product_uom = self._barcode_uom_id.id
            return
    
    # @api.onchange("x_scanned_barcode")
    # def onchange_x_scanned_barcode(self):
    #     print("\n\n--------------------------------")   
    #     product_id = self.env['product.product'].search([
    #             ('barcode', '=', dline.x_scanned_barcode)
    #         ], limit=1) 
    #     if product_id:



class StockMoveLine(models.Model):
    _inherit = 'stock.move.line'

    x_scanned_barcode = fields.Char(string="Barcode")
    _barcode_uom_id = fields.Many2one('uom.uom', string="Barcode UOM", store=False)
    description = fields.Char(string= 'Description')

    @api.model
    def create(self, vals):
        res = super().create(vals)
        if vals.get('x_scanned_barcode') and vals.get('description'):
            res.sudo().write({
                'x_scanned_barcode': vals.get('x_scanned_barcode'),
                'description': vals.get('description'),
            })
        return res

    def write(self, vals):
        for line in self:
            barcode_line = self.env['product.barcode.uom'].search([
                ('product_id', '=', line.product_id.product_tmpl_id.id),
                ('uom_id', '=', line.product_uom_id.id)
            ], limit=1)
            vals['x_scanned_barcode'] = barcode_line.barcode
            vals['description'] = barcode_line.description

        res = super().write(vals)
        return res

    # @api.constrains('qty_done')
    # def _check_product_uom_qty(self):
    #     for line in self:
    #         if line.qty_done <= 0:
    #             raise ValidationError("The quantity must be greater than 0.")

    @api.onchange('product_uom_id', 'qty_done')
    def onchange_uom(self):
        product_name = self.product_id.name or ''
        uom_name = self.product_uom_id.name or ''
        
        if 'UNIT' not in uom_name.upper():
            self.description = f"{product_name} X {uom_name}"
        else:
            self.description = product_name

        barcode_line = self.env['product.barcode.uom'].search([
            ('product_id', '=', self.product_id.product_tmpl_id.id),
            ('uom_id', '=', self.product_uom_id.id)
        ], limit=1)

        if barcode_line:
            self.x_scanned_barcode = barcode_line.barcode

        # ======= DYNAMIC QTY-BASED UOM SELECTION =======
        # if self.env.context.get('skip_uom_logic'):
        #     return  # Skip matching AND fallback if we just set qty=1

        # if self.product_id and self.product_qty:
        #     all_uoms = self.product_id.barcode_uom_ids.mapped('uom_id')
        #     qty_entered = self.product_qty
        #     match_found = False

        #     # Fetch barcode_line once
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

        #                 # Set qty=1 without triggering UoM change logic again
        #                 self = self.with_context(skip_uom_logic=True)
        #                 self.product_qty = 1

        #                 match_found = True
        #                 break

            # Fallback only if no match and qty is not 1
            # if not match_found and barcode_line and qty_entered != 1:
            #     _logger.info(f"=== NO MATCH, FALLBACK TO BARCODE UOM: {barcode_line.uom_id.name} ===")
            #     self.product_uom_id = barcode_line.uom_id.id

    @api.onchange('x_scanned_barcode', 'product_uom_qty')
    def _onchange_x_scanned_barcode(self):
        if not self.x_scanned_barcode:
            self._barcode_uom_id = False
            return
        barcode_line = self.env['product.barcode.uom'].search([
            ('barcode', '=', self.x_scanned_barcode)
        ], limit=1)
        if barcode_line:
            product = self.env['product.product'].search([
                ('product_tmpl_id', '=', barcode_line.product_id.id)
            ], limit=1)
            if product:
                self._barcode_uom_id = barcode_line.uom_id.id
                self.product_id = product.id
                self.product_uom_id = barcode_line.uom_id.id
                if not self.product_uom_qty:
                    self.product_uom_qty = 1.0
            else:
                self._barcode_uom_id = False

        # Second try: Internal reference match (if no barcode match and conditions apply)
        elif (len(self.x_scanned_barcode.strip()) <= 5):
            _logger.info("=== TRYING INTERNAL REFERENCE SEARCH ===")
            product = self.env['product.product'].search([
                ('default_code', '=', self.x_scanned_barcode)
            ], limit=1)
            if product:
                # Default to product's sales UoM
                self.product_id = product.id
                self.product_uom_id = product.uom_id.id
                self.product_uom_qty = 1
            else:
                _logger.warning("=== NO PRODUCT FOUND FOR INTERNAL REFERENCE ===")

        else:
            self._barcode_uom_id = False

        if barcode_line and self.product_id:
            if 'UNIT' not in (self.product_uom_id.name or '').upper():
                self.description = barcode_line.description or self.product_id.name + ' X ' + barcode_line.uom_id.name
            else:
                self.description = barcode_line.description or self.product_id.name

        if self.product_id:
            # Get allowed UoM IDs from product's barcode_uom_ids
            allowed_uoms = self.product_id.barcode_uom_ids.mapped('uom_id').ids
            return {
                'domain': {
                    'product_uom_id': [
                        ('id', 'in', allowed_uoms)
                    ]
                }
            }

        # ======= DYNAMIC QTY-BASED UOM SELECTION =======
        # if self.env.context.get('skip_uom_logic'):
        #     return  # Skip matching AND fallback if we just set qty=1

        # if self.product_id and self.product_qty:
        #     all_uoms = self.product_id.barcode_uom_ids.mapped('uom_id')
        #     qty_entered = self.product_qty
        #     match_found = False

        #     # Fetch barcode_line once
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

        #                 # Set qty=1 without triggering UoM change logic again
        #                 self = self.with_context(skip_uom_logic=True)
        #                 self.product_qty = 1

        #                 match_found = True
        #                 break

            # Fallback only if no match and qty is not 1
            if not match_found and barcode_line and qty_entered != 1:
                _logger.info(f"=== NO MATCH, FALLBACK TO BARCODE UOM: {barcode_line.uom_id.name} ===")
                self.product_uom_id = barcode_line.uom_id.id

    @api.onchange('product_id')
    def _onchange_product_id(self):
        if self.x_scanned_barcode and self._barcode_uom_id:
            self.product_uom_id = self._barcode_uom_id.id
            return
        if self.product_id:
            lang = self.env.context.get('lang') or self.env.user.lang
            product = self.product_id.with_context(lang=lang)
            self.product_uom_id = product.uom_id.id

    @api.onchange('product_uom_id')
    def _onchange_product_uom(self):
        if self.x_scanned_barcode and self._barcode_uom_id:
            if self.product_uom_id != self._barcode_uom_id:
                self.product_uom_id = self._barcode_uom_id.id
            return


class StockRequestLine(models.Model):
    _inherit = 'stock.request.lines'

    x_scanned_barcode = fields.Char(string="Barcode")

    @api.onchange('product_id')
    def _onchange_product_id(self):
        if self.product_id:
            return
            # self.description = self.product_id.name
            # self.product_uom = self.product_id.uom_id.id

    @api.onchange('x_scanned_barcode')
    def _onchange_x_scanned_barcode(self):
        if not self.x_scanned_barcode:
            return
        barcode_line = self.env['product.barcode.uom'].search([
            ('barcode', '=', self.x_scanned_barcode)
        ], limit=1)
        if barcode_line:
            self.product_id = barcode_line.product_id.id
            product = self.env['product.product'].search([
                ('product_tmpl_id', '=', barcode_line.product_id.id)
            ], limit=1)
            if product:
                self.product_uom = barcode_line.uom_id.id
                self.product_id = product.id
                if not self.product_qty:
                    self.product_qty = 1.0

        if 'UNIT' not in (self.product_uom.name or '').upper():
            self.description = barcode_line.description or self.product_id.name + ' X ' + barcode_line.uom_id.name
        else:
            self.description = barcode_line.description or self.product_id.name

        if self.product_id:
            # Get allowed UoM IDs from product's barcode_uom_ids
            allowed_uoms = self.product_id.barcode_uom_ids.mapped('uom_id').ids
            return {
                'domain': {
                    'product_uom': [
                        ('id', 'in', allowed_uoms)
                    ]
                }
            }

    @api.onchange('product_qty')
    def onchange_product_qty(self):
        # ======= DYNAMIC QTY-BASED UOM SELECTION =======
        if self.env.context.get('skip_uom_logic'):
            return  # Skip matching AND fallback if we just set qty=1

        if self.product_id and self.product_qty:
            all_uoms = self.product_id.barcode_uom_ids.mapped('uom_id')
            qty_entered = self.product_qty
            # match_found = False

            # Fetch barcode_line once
            barcode_line = None
            if self.x_scanned_barcode:
                barcode_line = self.env['product.barcode.uom'].search([
                    ('barcode', '=', self.x_scanned_barcode)
                ], limit=1)

            # for uom in all_uoms:
            #     match = re.search(r'\d+', uom.name)
            #     if match:
            #         multiplier = int(match.group(0))
            #         _logger.info(f"UOM Name: {uom.name} → Multiplier: {multiplier}")

            #         if multiplier == int(qty_entered):
            #             _logger.info(f"=== MATCH FOUND: QTY={qty_entered}, UOM={uom.name} ===")
            #             self.product_uom = uom.id

            #             # Set qty=1 without triggering UoM change logic again
            #             self = self.with_context(skip_uom_logic=True)
            #             self.product_qty = 1

            #             match_found = True
            #             break

            # # Fallback only if no match and qty is not 1
            # if not match_found and barcode_line and qty_entered != 1:
            #     _logger.info(f"=== NO MATCH, FALLBACK TO BARCODE UOM: {barcode_line.uom_id.name} ===")
            #     self.product_uom = barcode_line.uom_id.id



class StockPicking(models.Model):
    _inherit = 'stock.picking'

    def _cron_validate_stock_picking(self):
        pickings = self.search([
            ('state', 'not in', ['done', 'cancel']),
            ('sale_id.validate_picking', '=', True),
        ])

        for picking in pickings:
            try:
                picking.action_confirm_picking()
            except Exception as e:
                _logger.warning("Failed to validate picking %s: %s", picking.name, e)

        return True

    def action_confirm_picking(self):
        for picking in self:
            # If still in draft => confirm and assign
            if picking.state == 'draft':
                picking.action_confirm()
                if picking.state != 'assigned':
                    picking.action_assign()
                    if picking.state != 'assigned':
                        raise UserError(_("Could not reserve all requested products. Please use the \'Mark as Todo\' button to handle the reservation manually."))
            
            for move in picking.move_lines.filtered(lambda m: m.state not in ['done', 'cancel']):
                # for move_line in move.move_lines:
                move_line_vals = {
                    'move_id': move.id,
                    'picking_id': picking.id,
                    'product_id': move.product_id.id,
                    'product_uom_id': move.product_uom.id,
                    'location_id': move.location_id.id,
                    'location_dest_id': move.location_dest_id.id,
                    'company_id': picking.company_id.id,
                    'qty_done': move.product_uom_qty,
                    'product_uom_qty': move.product_uom_qty,
                    'x_scanned_barcode': move.x_scanned_barcode,
                    'description': move.description_picking,
                }
                self.env['stock.move.line'].sudo().create(move_line_vals)

            picking.button_validate()

    def _action_done(self):
        res = super(StockPicking, self)._action_done()

        for picking in self:
            for move in picking.move_lines:
                uom = move.product_uom

                # Dynamic description
                if uom and uom.name.lower() != "unit":
                    description = f"{move.product_id.display_name} X {uom.name}"
                else:
                    description = move.product_id.display_name

                for move_line in move.move_line_ids:
                    move_line.write({
                        'x_scanned_barcode': move.x_scanned_barcode,
                        'description': description,
                    })
        return res

    def action_assign(self):
        res = super(StockPicking, self).action_assign()
        for picking in self:
            for move in picking.move_lines:
                uom = move.product_uom

                # Dynamic description
                if uom and uom.name.lower() != "unit":
                    description = f"{move.product_id.display_name} X {uom.name}"
                else:
                    description = move.product_id.display_name

                for move_line in move.move_line_ids:
                    move_line.write({
                        'x_scanned_barcode': move.x_scanned_barcode,
                        'description': description,
                    })
        return res

    def action_confirm(self):
        res = super(StockPicking, self).action_confirm()
        for picking in self:
            for move in picking.move_lines:
                uom = move.product_uom

                # Dynamic description
                if uom and uom.name.lower() != "unit":
                    description = f"{move.product_id.display_name} X {uom.name}"
                else:
                    description = move.product_id.display_name

                for move_line in move.move_line_ids:
                    move_line.write({
                        'x_scanned_barcode': move.x_scanned_barcode,
                        'description': description,
                    })
        return res

    def get_barcode_view_state(self):
        pickings = super().get_barcode_view_state()

        for picking in pickings:
            for ml in picking['move_line_ids']:
                product_id = ml['product_id']['id']
                product_uom = ml.get('product_uom_id')

                product = self.env['product.product'].browse(product_id)
                parent_tmpl = product.product_tmpl_id.parent_template_id or product.product_tmpl_id

                uom_id = product_uom[0] if isinstance(product_uom, (list, tuple)) else product_uom

                barcode_line = self.env['product.barcode.uom'].search([
                    ('product_id', '=', parent_tmpl.id),
                    ('uom_id', '=', uom_id),
                ], limit=1)

                products = self.env['product.product'].search([
                    ('barcode', '=', barcode_line.barcode)
                ], limit=1)

                if barcode_line:
                    ml['product_id']['id'] = products.id
                    ml['product_id']['barcode'] = products.barcode
                    ml['product_id']['display_name'] = products.display_name
                    ml['product_barcode'] = products.barcode
                    ml['display_name'] = products.display_name or ml['display_name']

        return pickings

    def on_barcode_scanned(self, barcode):
        barcode_line = self.env['product.barcode.uom'].search([('barcode', '=', barcode)], limit=1)
        if barcode_line:
            product = barcode_line.product_id.product_variant_id
            qty = 1.0
            if barcode_line.uom_id:
                pass
            if self._check_product(product, qty):
                print("FAILED FAILED")
                return

        # Otherwise fallback to standard logic
        return super().on_barcode_scanned(barcode)