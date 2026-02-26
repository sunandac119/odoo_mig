
from odoo import models, fields, api

class ProductReplenishmentByParent(models.Model):
    _inherit = 'product.template'

    available_qty = fields.Float(string='Available Qty')
    unit_qty = fields.Float(string='Unit Qty')
    ctn_qty = fields.Float(string='Carton Qty')
    parent_template_id = fields.Many2one('product.template', string='Parent Template')
    vendor = fields.Many2one('res.partner', string='Vendor', domain=[('supplier', '=', True)])
    parent_available_qty = fields.Float(string='Parent Available Qty', compute='_compute_parent_available_qty')

    @api.depends('available_qty', 'unit_qty')
    def _compute_parent_available_qty(self):
        for record in self:
            record.parent_available_qty = record.available_qty * record.unit_qty

    @api.model
    def get_replenishment_by_parent(self):
        query = '''
        SELECT parent_template_id, SUM(available_qty), SUM(unit_qty), SUM(ctn_qty),
               SUM(available_qty * unit_qty) as parent_available_qty, vendor
        FROM product_template
        GROUP BY parent_template_id, vendor
        '''
        self.env.cr.execute(query)
        return self.env.cr.dictfetchall()
