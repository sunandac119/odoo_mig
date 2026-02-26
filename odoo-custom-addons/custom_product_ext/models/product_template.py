from odoo import models, fields, api

class ProductTemplate(models.Model):
    _inherit = 'product.template'

    parent_template_id = fields.Many2one('product.template', string='Parent Product Template')
    parent_qty_available = fields.Float('Parent Qty Available', compute='_compute_parent_qty_available')
    ctn_qty = fields.Float(string='CTN Qty', digits=(16, 2))
    unit_qty = fields.Float(string='Unit Qty', digits=(16, 2))
    unit_uom = fields.Float(string='Unit UOM', digits=(16, 2))
    total_cost = fields.Float(string='Total Cost', digits=(16, 2))
    total_done_qty = fields.Float(string='Total Done Qty', digits=(16, 2))
    purchase_cost = fields.Float(string='Purchase Cost', digits=(16, 2), compute='_compute_costs')
    sale_cost = fields.Float(string='Sale Cost', digits=(16, 2), compute='_compute_costs')
    sale_return_cost = fields.Float(string='Sale Return Cost', digits=(16, 2), compute='_compute_costs')
    purchase_return_cost = fields.Float(string='Purchase Return Cost', digits=(16, 2), compute='_compute_costs')
    warehouse_id = fields.Many2one('stock.warehouse',compute='_compute_warehouse_id', store=True, string="Warehouse")

    # @api.depends('qty_available')
    # def _compute_warehouse_id(self):
    #     for product in self:
    #         # Fetch the warehouses where the product is available
    #         stock_quant = self.env['stock.quant'].search([
    #             ('product_id', '=', product.id),
    #             ('quantity', '>', 0),
    #         ], limit=1)
    #         if stock_quant:
    #             product.warehouse_id = stock_quant.location_id.get_warehouse()
    #         else:
    #             product.warehouse_id = False




    @api.depends('qty_available')
    def _compute_warehouse_id(self):
        for product in self:
            # Fetch the warehouse where the product has available stock in internal locations
            stock_quant = self.env['stock.quant'].search([
                ('product_id', '=', product.id),
                ('quantity', '>', 0),
                ('location_id.usage', '=', 'internal')  # Ensure only internal locations are considered
            ], limit=1)

            if stock_quant:
                warehouse = stock_quant.location_id.get_warehouse()
                product.warehouse_id = warehouse if warehouse else False
            else:
                product.warehouse_id = False

    @api.depends('product_variant_ids.qty_available', 'unit_qty')
    def _compute_parent_qty_available(self):
        for template in self:
            if template.unit_qty != 0:
                if template.parent_template_id:
                    same_parent_templates = self.search([('parent_template_id', '=', template.parent_template_id.id)])
                    total_qty_available = 0.0
                    for product_template in same_parent_templates:
                        total_qty_available += sum(product_template.product_variant_ids.mapped(
                            lambda
                                variant: variant.qty_available * product_template.unit_qty * product_template.ctn_qty))
                    template.parent_qty_available = total_qty_available
                else:
                    template.parent_qty_available = sum(template.product_variant_ids.mapped(
                        lambda variant: variant.qty_available * template.unit_qty * template.ctn_qty))
            else:
                template.parent_qty_available = 0.0



    @api.depends('product_variant_ids.qty_available', 'unit_qty')
    def _compute_costs(self):
        for template in self:
            if template.unit_qty != 0:
                if template.parent_template_id:
                    same_parent_templates = self.search([('parent_template_id', '=', template.parent_template_id.id)])
                    total_purchase_cost = 0.0
                    total_sale_cost = 0.0
                    total_sale_return_cost = 0.0
                    total_purchase_return_cost = 0.0

                    for product_template in same_parent_templates:
                        moves = self.env['stock.move'].search([
                            ('product_id', 'in', product_template.product_variant_ids.ids),
                            ('state', '=', 'done'),
                        ])

                        for move in moves:
                            if move.purchase_line_id and not move.origin_returned_move_id:
                                total_purchase_cost += move.price_unit * move.quantity_done * product_template.unit_qty * product_template.ctn_qty
                            elif move.sale_line_id and not move.origin_returned_move_id:
                                total_sale_cost += move.sale_line_id.cost * move.quantity_done * product_template.unit_qty * product_template.ctn_qty
                            elif move.sale_line_id and move.origin_returned_move_id:
                                total_sale_return_cost += move.price_unit * move.quantity_done * product_template.unit_qty * product_template.ctn_qty
                            elif move.purchase_line_id and move.origin_returned_move_id:
                                # Update purchase_return_cost using price_unit from origin_returned_move_id
                                total_purchase_return_cost += move.origin_returned_move_id.price_unit * move.quantity_done * product_template.unit_qty * product_template.ctn_qty

                    template.purchase_cost = total_purchase_cost
                    template.sale_cost = total_sale_cost
                    template.purchase_return_cost = total_purchase_return_cost
                    template.sale_return_cost = total_sale_return_cost
                else:
                    template.purchase_cost = sum(template.product_variant_ids.filtered(
                        lambda variant: variant.purchase_line_id and not variant.origin_returned_move_id).mapped(
                        lambda variant: variant.purchase_cost * template.unit_qty * template.ctn_qty))
                    template.sale_cost = sum(template.product_variant_ids.filtered(
                        lambda variant: variant.sale_line_id and not variant.origin_returned_move_id).mapped(
                        lambda variant: variant.sale_cost * template.unit_qty * template.ctn_qty))
                    template.purchase_return_cost = sum(template.product_variant_ids.filtered(
                        lambda variant: variant.purchase_line_id and variant.origin_returned_move_id).mapped(
                        lambda variant: variant.purchase_return_cost * template.unit_qty * template.ctn_qty))
                    template.sale_return_cost = sum(template.product_variant_ids.filtered(
                        lambda variant: variant.sale_line_id and variant.origin_returned_move_id).mapped(
                        lambda variant: variant.sale_return_cost * template.unit_qty * template.ctn_qty))
            else:
                template.purchase_cost = 0.0
                template.sale_cost = 0.0
                template.purchase_return_cost = 0.0
                template.sale_return_cost = 0.0

    @api.model
    def cron_update_standard_price(self):
        product_templates = self.search([('parent_template_id', '!=', False)])

        for template in product_templates:
            same_parent_templates = self.search([('parent_template_id', '=', template.parent_template_id.id)])

            total_purchase_cost = 0.0
            total_sales_cost = 0.0
            total_purchase_return_cost = 0.0
            total_sale_return_cost = 0.0
            total_purchase_done_qty = 0.0
            total_sales_done_qty = 0.0
            total_purchase_return_done_qty = 0.0
            total_sale_return_done_qty = 0.0

            for product_template in same_parent_templates:
                moves = self.env['stock.move'].search([
                    ('product_id', 'in', product_template.product_variant_ids.ids),
                    ('state', '=', 'done'),
                ])

                for move in moves:
                    if move.purchase_line_id and move.origin_returned_move_id:
                        total_purchase_return_cost += move.origin_returned_move_id.price_unit * move.quantity_done
                        total_purchase_return_done_qty += move.quantity_done * product_template.unit_qty
                    elif move.sale_line_id and not move.origin_returned_move_id:
                        total_sales_cost += move.sale_line_id.cost * move.quantity_done
                        total_sales_done_qty += move.quantity_done * product_template.unit_qty
                        if move.sale_line_id.cost == 0.0:
                            move.sale_line_id.cost = product_template.standard_price
                            move.price_unit = move.sale_line_id.cost
                    elif move.purchase_line_id and not move.origin_returned_move_id:
                        total_purchase_cost += move.price_unit * move.quantity_done
                        total_purchase_done_qty += move.quantity_done * product_template.unit_qty
                    elif move.sale_line_id and move.origin_returned_move_id:
                        total_sale_return_cost += move.price_unit * move.quantity_done
                        total_sale_return_done_qty += move.quantity_done * product_template.unit_qty

            total_cost = total_purchase_cost - total_sales_cost + total_sale_return_cost - total_purchase_return_cost
            total_done_qty = total_purchase_done_qty - total_sales_done_qty + total_sale_return_done_qty - total_purchase_return_done_qty

            if total_done_qty != 0:
                new_standard_price = total_cost / total_done_qty

                for product_template in same_parent_templates:
                    updated_price = new_standard_price * product_template.unit_qty
                    product_template.write({'standard_price': updated_price})
                    product_template.write({'total_cost': total_cost})
                    product_template.write({'total_done_qty': total_done_qty})

class Orderpoint(models.Model):
    _inherit = "stock.warehouse.orderpoint"


    unit_qty = fields.Float(string='Unit Qty', related='product_id.product_tmpl_id.unit_qty', store=True)
    ctn_qty = fields.Float(string='CTN Qty', related='product_id.product_tmpl_id.ctn_qty', store=True)
    # parent_qty_available = fields.Float(string='Parent Qty Available'
    #                                     ,compute='_compute_parent_qty_available', store=True)
    parent_on_hand_qty = fields.Float(string='Parent QOH', compute='_compute_parent_on_hand_qty', store=True)

    warehouse_id = fields.Many2one('stock.warehouse', string='Warehouse', related='product_id.warehouse_id',
                                   store=True)
    parent_template_id = fields.Many2one('product.template', string='Parent Product Template',
                                         related='product_id.product_tmpl_id.parent_template_id', store=True)
    product_on_hand_qty = fields.Float(string='QOH', related='product_id.product_tmpl_id.qty_available', store=True)
    parent_product_ctn_qty = fields.Float(related='parent_template_id.ctn_qty',string="Parent CTN QTY")

    @api.onchange('warehouse_id')
    def _onchange_warehouse_id(self):
        for record in self:
            if record.warehouse_id:
                # Set the location_id based on the warehouse's main stock location
                record.location_id = record.warehouse_id.lot_stock_id.id
            else:
                record.location_id = False

    @api.depends('parent_template_id')
    def _compute_parent_on_hand_qty(self):
        for orderpoint in self:
            parent_template = orderpoint.parent_template_id
            if parent_template:
                orderpoint.parent_on_hand_qty = sum(parent_template.product_variant_ids.mapped('qty_available'))
            else:
                orderpoint.parent_on_hand_qty = 0.0

    @api.model
    def create(self, vals):
        # Ensure location_id is set, either from the warehouse or as a default
        if not vals.get('location_id'):
            if 'warehouse_id' in vals:
                warehouse = self.env['stock.warehouse'].browse(vals['warehouse_id'])
                vals['location_id'] = warehouse.lot_stock_id.id  # Default to the warehouse's stock location
            else:
                raise models.ValidationError('Location must be specified for the warehouse orderpoint.')
        return super(Orderpoint, self).create(vals)

    def write(self, vals):
        if not vals.get('location_id'):
            for rec in self:
                if not rec.location_id:
                    if rec.warehouse_id:
                        vals['location_id'] = rec.warehouse_id.lot_stock_id.id
                    else:
                        raise models.ValidationError('Location must be specified for the warehouse orderpoint.')
        return super(Orderpoint, self).write(vals)



