# -*- coding: utf-8 -*-
from odoo import fields, models,api, _
from odoo.exceptions import UserError
from odoo.tests import Form

class StockPicking(models.Model):
    _inherit = 'stock.move'

    return_line_id = fields.Many2one('purchase.return.line')


class StockPicking(models.Model):
    _inherit = 'stock.picking'

    is_return = fields.Boolean(string="Purchase return")
    return_id = fields.Many2one('purchase.return')



    def button_validate(self):
        res = super(StockPicking,self).button_validate()
        if self.move_ids_without_package and  self.return_id  and self.state == 'done':
            invoice = self.sudo().return_id.invoice_ids.filtered(lambda r:r.picking_id.id == self.id)
            if not invoice:
                self.sudo().create_vendor_credit()
        return res

    def create_vendor_credit(self):
        for picking_id in self:
            current_user = self.env.uid
            if picking_id.picking_type_id.code == 'outgoing':
                vendor_journal_id = picking_id.sudo().return_id.return_journal_id.id
                invoice_line_list = []
                lines = picking_id.move_ids_without_package.sudo().filtered(lambda r:r.quantity_done > 0 )
                for move in lines:
                    if move.quantity_done>0 :
                        vals = (0, 0, {
                            'name': move.description_picking or move.return_line_id.product_id.name,
                            'x_scanned_barcode': move.x_scanned_barcode,
                            # 'name': move.return_line_id.product_id.name,
                            'product_id': move.return_line_id.product_id.id,
                            'price_unit': move.return_line_id.price_unit,
                            'tax_ids': [(6, 0, move.return_line_id.tax_id.ids)],
                            'quantity': move.quantity_done,
                            'return_line_id': move.return_line_id.id,
                        })
                        invoice_line_list.append(vals)
                if invoice_line_list:
                    invoice = picking_id.env['account.move'].sudo().create({
                        'move_type': 'in_refund',
                        'invoice_origin': picking_id.name,
                        'invoice_user_id': current_user,
                        'partner_id': picking_id.partner_id.id,
                        'currency_id': picking_id.env.company.currency_id.id,
                        'journal_id': int(vendor_journal_id),
                        'ref': "Purchase Return %s"%picking_id.name,
                        'picking_id': picking_id.id,
                        'return_id': picking_id.return_id.id,
                        'invoice_line_ids': invoice_line_list
                    })

                    return invoice



