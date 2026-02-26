from odoo import models, fields, api, tools
from odoo.exceptions import ValidationError
from datetime import datetime, date
import logging

_logger = logging.getLogger(__name__)


class ProductBarcodeUoM(models.Model):
    _name = 'product.barcode.uom'
    _description = 'Product Barcode by UOM'
    _rec_name = 'barcode'
    _order = 'product_id, uom_id'

    product_id = fields.Many2one('product.template', string="Product", required=True, ondelete='cascade')
    uom_id = fields.Many2one('uom.uom', string="Unit of Measure", required=True)
    barcode = fields.Char(string="Barcode", required=True, index=True)
    sale_price = fields.Float(string="Sale Price", digits='Product Price', default=0.0)
    active = fields.Boolean(string="Active", default=True)
    company_id = fields.Many2one('res.company', string='Company', default=lambda self: self.env.company)
    description = fields.Char(string="Description")
    
    uom_category_id = fields.Many2one(
        'uom.category',
        string='UOM Category',
        # compute='_compute_uom_category',
        related='product_id.uom_category_id',
        store=True,
        readonly=True
    )

    # _sql_constraints = [
    #     ('barcode_unique', 'UNIQUE(barcode)', 'Barcode must be unique across all products!'),
    #     ('product_uom_unique', 'UNIQUE(product_id, uom_id)', 'Only one barcode per product-UOM combination is allowed!'),
    # ]

    @api.constrains('barcode')
    def _check_barcode(self):
        for record in self:
            if not record.barcode or not record.barcode.strip():
                raise ValidationError("Barcode cannot be empty!")

    @api.constrains('uom_id', 'product_id')
    def _check_uom_category(self):
        for record in self:
            if record.product_id and record.uom_id:
                if record.product_id.uom_category_id != record.uom_id.category_id:
                    raise ValidationError(
                        f"The UOM '{record.uom_id.name}' is not compatible with product '{record.product_id.name}'. "
                        f"Please select a UOM from the '{record.product_id.uom_category_id.name}' category."
                    )

    @api.onchange('product_id')
    def _onchange_product_id(self):
        if self.product_id:
            self.uom_id = False
            domain = [('active', '=', True)]
            if self.product_id.uom_category_id:
                domain.append(('category_id', '=', self.product_id.uom_category_id.id))
            return {'domain': {'uom_id': domain}}
        return {'domain': {'uom_id': [('active', '=', True)]}}

    @api.onchange('uom_category_id')
    def _onchange_uom_category_id(self):
        if self.uom_category_id:
            self.uom_id = False
            domain = [('active', '=', True), ('category_id', '=', self.uom_category_id.id)]
            return {'domain': {'uom_id': domain}}
        return {'domain': {'uom_id': [('active', '=', True)]}}

    def name_get(self):
        result = []
        for record in self:
            name = f"{record.product_id.name} - {record.uom_id.name} ({record.barcode})"
            result.append((record.id, name))
        return result

    @api.model
    def name_search(self, name='', args=None, operator='ilike', limit=100):
        if args is None:
            args = []
        domain = args.copy()
        if name:
            domain = ['|', '|',
                      ('barcode', operator, name),
                      ('product_id.name', operator, name),
                      ('product_id.default_code', operator, name)] + domain
        records = self.search(domain, limit=limit)
        return records.name_get()


