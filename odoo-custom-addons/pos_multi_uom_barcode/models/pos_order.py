from odoo import models, fields, api
from collections import defaultdict

class PosOrderLine(models.Model):
    _inherit = 'pos.order.line'

    uom_id = fields.Many2one('uom.uom', string="UOM")

    @api.model
    def create(self, vals):
        if vals.get('product_uom_id'):
            vals['uom_id'] = int(vals.get('product_uom_id'))
        res = super(PosOrderLine, self).create(vals)
        return res


class StockPicking(models.Model):
    _inherit = 'stock.picking'

    # def _prepare_stock_move_vals(self, first_line, order_lines):
    #     return {
    #         'name': first_line.name,
    #         'product_uom': first_line.uom_id.id or first_line.product_id.uom_id.id,
    #         'picking_id': self.id,
    #         'picking_type_id': self.picking_type_id.id,
    #         'product_id': first_line.product_id.id,
    #         'product_uom_qty': abs(sum(first_line.mapped('qty'))),
    #         'state': 'draft',
    #         'location_id': self.location_id.id,
    #         'location_dest_id': self.location_dest_id.id,
    #         'company_id': self.company_id.id,
    #     }

    def _prepare_stock_move_vals(self, first_line, order_lines):
        product = first_line.product_id
        uom = first_line.uom_id or product.uom_id
        barcode_line = product.barcode_uom_ids.filtered(lambda l: l.uom_id == uom)[:1]
        scanned_barcode = barcode_line.barcode if barcode_line else product.barcode
        description = barcode_line.description if barcode_line else first_line.name

        return {
            'name': first_line.name,
            'description_picking': description,
            'x_scanned_barcode': scanned_barcode,
            'product_uom': uom.id,
            'picking_id': self.id,
            'picking_type_id': self.picking_type_id.id,
            'product_id': product.id,
            'product_uom_qty': abs(sum(first_line.mapped('qty'))),
            'state': 'draft',
            'location_id': self.location_id.id,
            'location_dest_id': self.location_dest_id.id,
            'company_id': self.company_id.id,
        }

    def _create_move_from_pos_order_lines(self, lines):
        self.ensure_one()
        move_vals = []
        lines_data = defaultdict(dict)

        for line in lines:
            move_val = self._prepare_stock_move_vals(line, self.env['pos.order.line'].browse([line.id]))
            move_vals.append(move_val)
            lines_data[line.product_id.id].setdefault('order_lines', self.env['pos.order.line'].browse())
            lines_data[line.product_id.id]['order_lines'] += line

        moves = self.env['stock.move'].create(move_vals)

        for move in moves:
            lines_data[move.product_id.id].update({'move': move})

        confirmed_moves = moves._action_confirm()

        confirmed_moves_to_assign = confirmed_moves.filtered(
            lambda m: m.product_id.id not in lines_data or m.product_id.tracking == 'none'
        )
        self._create_move_lines_for_pos_order(confirmed_moves_to_assign, set_quantity_done_on_move=True)

        confirmed_moves_remaining = confirmed_moves - confirmed_moves_to_assign

        if self.picking_type_id.use_existing_lots or self.picking_type_id.use_create_lots:
            existing_lots = self._create_production_lots_for_pos_order(lines)
            move_lines_to_create = []

            for move in confirmed_moves_remaining:
                for line in lines_data[move.product_id.id]['order_lines']:
                    sum_of_lots = 0
                    for lot in line.pack_lot_ids.filtered(lambda l: l.lot_name):
                        qty = 1 if line.product_id.tracking == 'serial' else abs(line.qty)
                        ml_vals = dict(move._prepare_move_line_vals(), qty_done=qty)

                        if existing_lots:
                            existing_lot = existing_lots.filtered_domain([
                                ('product_id', '=', line.product_id.id),
                                ('name', '=', lot.lot_name)
                            ])
                            quant = self.env['stock.quant']
                            if existing_lot:
                                quant = self.env['stock.quant'].search([
                                    ('lot_id', '=', existing_lot.id),
                                    ('quantity', '>', '0.0'),
                                    ('location_id', 'child_of', move.location_id.id)
                                ], order='id desc', limit=1)

                            ml_vals.update({
                                'lot_id': existing_lot.id if existing_lot else False,
                                'location_id': quant.location_id.id if quant else move.location_id.id,
                                'owner_id': quant.owner_id.id if quant else False,
                            })
                        else:
                            ml_vals.update({'lot_name': lot.lot_name})

                        move_lines_to_create.append(ml_vals)
                        sum_of_lots += qty

                    if abs(line.qty) != sum_of_lots:
                        difference_qty = abs(line.qty) - sum_of_lots
                        ml_vals = move._prepare_move_line_vals()
                        if line.product_id.tracking == 'serial':
                            ml_vals.update({'qty_done': 1})
                            move_lines_to_create.extend([ml_vals.copy() for _ in range(int(difference_qty))])
                        else:
                            ml_vals.update({'qty_done': difference_qty})
                            move_lines_to_create.append(ml_vals)

            self.env['stock.move.line'].create(move_lines_to_create)
        else:
            self._create_move_lines_for_pos_order(confirmed_moves_remaining)


