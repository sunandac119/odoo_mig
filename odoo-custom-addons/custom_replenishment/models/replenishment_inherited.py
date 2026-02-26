# -*- coding: utf-8 -*-
##############################################################################
# Author      : Acespritech Solutions Pvt. Ltd. (<www.acespritech.com>)
# Copyright(c): 2012-Present Acespritech Solutions Pvt. Ltd.
# All Rights Reserved.
#
# This program is copyright property of the author mentioned above.
# You can`t redistribute it and/or modify it.
#
##############################################################################

from odoo import models, fields, api
from odoo.exceptions import ValidationError


# class Orderpoint(models.Model):
#     _inherit = "stock.warehouse.orderpoint"
#
#
#     unit_qty = fields.Float(string='Unit Qty', related='product_id.product_tmpl_id.unit_qty', store=True)
#     ctn_qty = fields.Float(string='CTN Qty', related='product_id.product_tmpl_id.ctn_qty', store=True)
#     parent_on_hand_qty = fields.Float(string='Parent QOH', compute='_compute_parent_on_hand_qty', store=True)
#
#     warehouse_id = fields.Many2one(
#         'stock.warehouse',
#         string='Warehouse',
#         required=True
#     )
#     parent_template_id = fields.Many2one(
#         'product.template',
#         string='Parent Product Template',
#         related='product_id.product_tmpl_id.parent_template_id',
#         store=True
#     )
#
#     product_on_hand_qty = fields.Float(
#         string='QOH',
#         compute='_compute_product_on_hand_qty',
#         store=True
#     )
#     parent_product_ctn_qty = fields.Float(
#         related='parent_template_id.ctn_qty',
#         string="Parent CTN QTY"
#     )
#
#     location_id = fields.Many2one(
#         'stock.location',
#         string='Location',
#         required=True,
#         compute='_compute_location_id',
#         store=True
#     )
#
#     @api.depends('warehouse_id')
#     def _compute_location_id(self):
#         for orderpoint in self:
#             if orderpoint.warehouse_id:
#                 orderpoint.location_id = orderpoint.warehouse_id.lot_stock_id.id
#             else:
#                 orderpoint.location_id = False
#
#     @api.depends('product_id.qty_available')
#     def _compute_product_on_hand_qty(self):
#         for orderpoint in self:
#             orderpoint.product_on_hand_qty = orderpoint.product_id.qty_available
#
#     @api.depends('parent_template_id', 'parent_template_id.product_variant_ids.qty_available')
#     def _compute_parent_on_hand_qty(self):
#         for orderpoint in self:
#             parent_template = orderpoint.parent_template_id
#             if parent_template:
#                 orderpoint.parent_on_hand_qty = sum(parent_template.product_variant_ids.mapped('qty_available'))
#             else:
#                 orderpoint.parent_on_hand_qty = 0.0
#
#     @api.model
#     def create(self, vals):
#         # Ensure warehouse_id is set before creation
#         if 'warehouse_id' not in vals or not vals.get('warehouse_id'):
#             raise models.ValidationError('Warehouse must be specified for the warehouse orderpoint.')
#         return super(Orderpoint, self).create(vals)
#
#     def write(self, vals):
#         # Ensure warehouse_id is set before updating
#         if 'warehouse_id' in vals and not vals.get('location_id'):
#             warehouse = self.env['stock.warehouse'].browse(vals['warehouse_id'])
#             if warehouse:
#                 vals['location_id'] = warehouse.lot_stock_id.id
#             else:
#                 raise models.ValidationError('Location must be specified for the warehouse orderpoint.')
#         return super(Orderpoint, self).write(vals)




class Orderpoint(models.Model):
    _inherit = "stock.warehouse.orderpoint"

    unit_qty = fields.Float(string='Unit Qty', related='product_id.product_tmpl_id.unit_qty', store=True)
    ctn_qty = fields.Float(string='CTN Qty', related='product_id.product_tmpl_id.ctn_qty', store=True)
    parent_on_hand_qty = fields.Float(string='Parent QOH', compute='_compute_parent_on_hand_qty', store=True)

    warehouse_id = fields.Many2one(
        'stock.warehouse',
        string='Warehouse',
        required=True
    )
    parent_template_id = fields.Many2one(
        'product.template',
        string='Parent Product Template',
        related='product_id.product_tmpl_id.parent_template_id',
        store=True
    )

    product_on_hand_qty = fields.Float(
        string='QOH',
        compute='_compute_product_on_hand_qty',
        store=True
    )
    parent_product_ctn_qty = fields.Float(
        related='parent_template_id.ctn_qty',
        string="Parent CTN QTY"
    )

    location_id = fields.Many2one(
        'stock.location',
        string='Location',
        required=True,
        compute='_compute_location_id',
        store=True
    )

    # parent_unit_qty = fields.Float(
    #     string='Parent Unit Qty',
    #     compute='_compute_parent_unit_qty',
    #     store=True
    # )

    parent_unit_qty = fields.Float(
        string='Parent Unit Qty',
        related='parent_template_id.unit_qty', readonly=False, related_sudo=False
        # store=True
    )

    # replenishment_required = fields.Boolean(
    #     string="Replenishment Required",
    #     compute='_compute_replenishment_required',
    #     store=True
    # )

    # New field for total on-hand quantity in unit_qty
    total_on_hand_qty = fields.Float(
        string='Total On Hand Qty (in Units)',
        compute='_compute_total_on_hand_qty',
        store=True
    )

    # replenishment_required = fields.Boolean(
    #     string='Replenishment Required',
    #     compute='_compute_replenishment_required',
    #     store=True
    # )

    # @api.depends('parent_on_hand_qty', 'product_min_qty')
    # def _compute_replenishment_required(self):
    #     for orderpoint in self:
    #         reorder_rule = self.env['stock.warehouse.orderpoint'].search([('id', '=', orderpoint.id)])
    #         if reorder_rule and reorder_rule.min_qty:
    #             orderpoint.replenishment_required = orderpoint.parent_on_hand_qty < reorder_rule.min_qty
    #         else:
    #             orderpoint.replenishment_required = False

    @api.depends('warehouse_id')
    def _compute_location_id(self):
        for orderpoint in self:
            if orderpoint.warehouse_id:
                orderpoint.location_id = orderpoint.warehouse_id.lot_stock_id.id
            else:
                orderpoint.location_id = False

    @api.depends('product_id.qty_available')
    def _compute_product_on_hand_qty(self):
        for orderpoint in self:
            orderpoint.product_on_hand_qty = orderpoint.product_id.qty_available

    @api.depends('parent_template_id', 'parent_template_id.product_variant_ids.qty_available')
    def _compute_parent_on_hand_qty(self):
        for orderpoint in self:
            parent_template = orderpoint.parent_template_id
            if parent_template:
                orderpoint.parent_on_hand_qty = sum(parent_template.product_variant_ids.mapped('qty_available'))
            else:
                orderpoint.parent_on_hand_qty = 0.0

    # @api.depends('parent_template_id')
    # def _compute_parent_unit_qty(self):
    #     for orderpoint in self:
    #         print("\n\n\n orderpoint", orderpoint)
    #         if orderpoint.parent_template_id:
    #             print("\n\n\n orderpoint parent_unit_qty", orderpoint.parent_unit_qty)
    #             orderpoint.parent_unit_qty = orderpoint.parent_template_id.unit_qty
    #         else:
    #             orderpoint.parent_unit_qty = 0.0

    # @api.depends('parent_unit_qty', 'product_min_qty')
    # def _compute_replenishment_required(self):
    #     for orderpoint in self:
    #         # Ensure parent_unit_qty and min_qty are compared correctly
    #         if orderpoint.parent_unit_qty < orderpoint.product_min_qty:
    #             orderpoint.replenishment_required = True
    #         else:
    #             orderpoint.replenishment_required = False

    @api.constrains('unit_qty', 'product_min_qty')
    def _check_reorder_rule(self):
        for rule in self:
            if rule.parent_unit_qty < rule.product_min_qty:
                return True
            else:
                # raise ValidationError(
                #     'Reorder cannot be done because the Parent Unit Quantity exceeds the minimum reorder quantity.'
                # )
                pass


    @api.depends('parent_on_hand_qty', 'unit_qty')
    def _compute_total_on_hand_qty(self):
        for orderpoint in self:
            if orderpoint.ctn_qty:
                # Calculating total on-hand quantity in units
                orderpoint.total_on_hand_qty = orderpoint.parent_on_hand_qty * orderpoint.unit_qty
            else:
                orderpoint.total_on_hand_qty = 0.0

    @api.model
    def create(self, vals):
        # Ensure warehouse_id is set before creation
        if 'warehouse_id' not in vals or not vals.get('warehouse_id'):
            raise models.ValidationError('Warehouse must be specified for the warehouse orderpoint.')
        return super(Orderpoint, self).create(vals)

    def write(self, vals):
        # Ensure warehouse_id is set before updating
        if 'warehouse_id' in vals and not vals.get('location_id'):
            warehouse = self.env['stock.warehouse'].browse(vals['warehouse_id'])
            if warehouse:
                vals['location_id'] = warehouse.lot_stock_id.id
            else:
                raise models.ValidationError('Location must be specified for the warehouse orderpoint.')
        return super(Orderpoint, self).write(vals)




# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:
