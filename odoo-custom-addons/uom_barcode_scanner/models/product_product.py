from odoo import models, fields, api
from odoo.exceptions import ValidationError
from datetime import datetime, date
from odoo.tools import float_compare


class ProductProduct(models.Model):
    _inherit = 'product.product'

    is_weight = fields.Boolean(string="Weight Product", default=False)
    
    @api.model
    def name_search(self, name='', args=None, operator='ilike', limit=100):
        if args is None:
            args = []
        
        if name:
            barcode_records = self.env['product.barcode.uom'].search([
                ('barcode', '=', name),
                ('active', '=', True)
            ], limit=1)
            
            if barcode_records:
                barcode_rec = barcode_records[0]
                product_variants = barcode_rec.product_id.product_variant_ids.filtered('active')
                if product_variants:
                    product_variant = product_variants[0]
                    return [(product_variant.id, f"{product_variant.display_name} [{barcode_rec.barcode}] - {barcode_rec.uom_id.name}")]
        
        result = super().name_search(name, args, operator, limit)
        
        if name and len(result) < limit:
            barcode_records = self.env['product.barcode.uom'].search([
                ('barcode', operator, name),
                ('active', '=', True)
            ], limit=limit - len(result))
            
            existing_ids = [r[0] for r in result]
            for barcode_rec in barcode_records:
                product_variants = barcode_rec.product_id.product_variant_ids.filtered('active')
                for product_variant in product_variants:
                    if product_variant.id not in existing_ids:
                        result.append((product_variant.id, 
                                     f"{product_variant.display_name} [{barcode_rec.barcode}] - {barcode_rec.uom_id.name}"))
                        existing_ids.append(product_variant.id)
                        break
        
        return result


    def _select_seller(self, partner_id=False, quantity=0.0, date=None, uom_id=False, params=False):
        self.ensure_one()
        if date is None:
            date = fields.Date.context_today(self)
        precision = self.env['decimal.precision'].precision_get('Product Unit of Measure')

        res = self.env['product.supplierinfo']
        sellers = self._prepare_sellers(params)
        sellers = sellers.filtered(lambda s: not s.company_id or s.company_id.id == self.env.company.id)
        for seller in sellers:
            # Set quantity in UoM of seller
            quantity_uom_seller = quantity
            if uom_id and uom_id != seller.product_uom:
                continue
            if quantity_uom_seller and uom_id:
                quantity_uom_seller = uom_id._compute_quantity(quantity_uom_seller, seller.product_uom)
            if seller.date_start and seller.date_start > date:
                continue
            if seller.date_end and seller.date_end < date:
                continue
            if partner_id and seller.name not in [partner_id, partner_id.parent_id]:
                continue
            if quantity is not None and float_compare(quantity_uom_seller, seller.min_qty, precision_digits=precision) == -1:
                continue
            if seller.product_id and seller.product_id != self:
                continue
            if not res or res.name == seller.name:
                res |= seller
        return res.sorted('price')[:1]


class SupplierInfo(models.Model):
    _inherit = "product.supplierinfo"

    product_uom = fields.Many2one(
        'uom.uom',store=True,
        string='Unit of Measure',
        help="Unit of Measure used for purchases from this vendor.")

    @api.model
    def create(self, vals):
        res = super().create(vals)
        if vals.get('product_uom'):
            res.sudo().write({'product_uom':int(vals.get('product_uom'))})
        return res

