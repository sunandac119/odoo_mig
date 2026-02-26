# -*- coding: utf-8 -*-
# This module and its content is copyright of Technaureus Info Solutions Pvt. Ltd.
# - © Technaureus Info Solutions Pvt. Ltd 2020. All rights reserved.

from odoo import models, fields, _


class StockCheckingWizard(models.TransientModel):
    _name = "stock.checking.wizard"
    _inherit = 'barcodes.barcode_events_mixin'
    _description = 'Wizard to read barcode on inventory'

    product_id = fields.Many2one('product.product', default=None)
    last_barcode = fields.Char(string='Last Barcode')
    prod_lot_id = fields.Many2one('stock.production.lot', string='Lot/Serial Number')
    product_tracking = fields.Selection('Tracking', related='product_id.tracking')
    company_id = fields.Many2one(
        'res.company', 'Company',
        default=lambda self: self.env.company,
        index=True, required=True)
    message = fields.Char(string="Message", readonly=True, default="Scan Products")
    type_msg = fields.Selection([
        ('info', 'Info'),
        ('not_found', 'Not found'),
        ('success', 'Success'),
    ], default='info', readonly=True)

    def on_barcode_scanned(self, barcode):
        inventory_id = self.env['stock.inventory'].browse(self._context.get('active_id'))
        product_id = self.env['product.product'].search([('barcode', '=', barcode)])
        if not product_id:
            self.last_barcode = None
            self.type_msg = 'not_found'
            self.message = "Product not found!"
        if len(product_id) > 1:
            self.last_barcode = None
            self.type_msg = 'not_found'
            self.message = 'More than one product found!'
        if product_id and inventory_id.product_ids:
            if product_id.id not in inventory_id.product_ids.ids:
                self.last_barcode = None
                self.product_id = None
                self.type_msg = 'not_found'
                self.message = "The Product is not in the Selected Product List!"
                return
        if barcode and product_id and inventory_id:
            self.type_msg = 'success'
            self.message = "Barcode read successfully"
            self.last_barcode = barcode + ' - ' + product_id.display_name
            self.product_id = product_id
            if product_id.tracking != "none":
                self.type_msg = 'info'
                self.message = "Select Lot/Serial Number"
                return
            if product_id.tracking == 'none':
                lines = inventory_id.line_ids.filtered(lambda x: x.product_id == product_id)
                if lines:
                    lines[0].write({'product_qty': lines[0].product_qty + 1})
                else:
                    product_data = {
                        'inventory_id': inventory_id.id,
                        'product_id': product_id.id,
                        'product_uom_id': product_id.uom_id.id,
                        'location_id': inventory_id.location_ids.id,
                        'product_qty': 1,
                    }
                    self.env['stock.inventory.line'].create(product_data)

    def button_lot_confirm(self):
        inventory_id = self.env['stock.inventory'].browse(self._context.get('active_id'))
        if self.product_id and self.product_id.tracking == 'lot' and self.prod_lot_id and inventory_id:
            lines = inventory_id.line_ids.filtered(lambda x: x.prod_lot_id == self.prod_lot_id)
            if lines:
                lines[0].write({'product_qty': lines[0].product_qty + 1})
            else:
                product_data = {
                    'inventory_id': inventory_id.id,
                    'product_id': self.product_id.id,
                    'product_uom_id': self.product_id.uom_id.id,
                    'location_id': inventory_id.location_ids.id,
                    'prod_lot_id': self.prod_lot_id.id,
                    'product_qty': 1,
                }
                self.env['stock.inventory.line'].create(product_data)
        elif self.product_id and self.product_id.tracking == 'serial' and self.prod_lot_id and inventory_id:
            product_data = {
                'inventory_id': inventory_id.id,
                'product_id': self.product_id.id,
                'product_uom_id': self.product_id.uom_id.id,
                'location_id': inventory_id.location_ids.id,
                'prod_lot_id': self.prod_lot_id.id,
                'product_qty': 1,
            }
            self.env['stock.inventory.line'].create(product_data)
        return {
            'name': _('Scan Barcode'),
            'view_type': 'form',
            'view_mode': 'form',
            'res_model': 'stock.checking.wizard',
            'view_id': self.env.ref('tis_stock_checking.view_stock_checking_wizard_form').id,
            'type': 'ir.actions.act_window',
            'context': {'active_id': inventory_id.id},
            'target': 'new',
        }
