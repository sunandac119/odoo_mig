from odoo import models, fields, api
from odoo.exceptions import ValidationError
from datetime import datetime, date

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
    uom_category_id = fields.Many2one(
        'uom.category',
        string='UOM Category',
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
class PricelistItem(models.Model):
    _inherit = 'product.pricelist.item'
    
    pricelist_uom_id = fields.Many2one('uom.uom', string='UOM')
class ProductPricelist(models.Model):
    _inherit = 'product.pricelist'
    
    def _normalize_date(self, date_input):
        if not date_input:
            return fields.Date.today()
        if isinstance(date_input, str):
            try:
                return fields.Date.from_string(date_input)
            except:
                return fields.Date.today()
        if isinstance(date_input, datetime):
            return date_input.date()
        return date_input

    def get_pricelist_price_for_barcode(self, product_id, uom_id, quantity=1.0, date=None):
        self.ensure_one()
        date = self._normalize_date(date)
        
        domain = [
            ('pricelist_id', '=', self.id),
            '|', ('date_start', '=', False), ('date_start', '<=', date),
            '|', ('date_end', '=', False), ('date_end', '>=', date),
            ('min_quantity', '<=', quantity),
        ]
        
        product = self.env['product.product'].browse(product_id)
        if not product.exists():
            return 0.0
        
        product_tmpl_id = product.product_tmpl_id.id
        
        uom_specific_items = self.env['product.pricelist.item'].search(
            domain + [
                '|', ('product_id', '=', product_id), ('product_tmpl_id', '=', product_tmpl_id),
                ('pricelist_uom_id', '=', uom_id)
            ],
            order='pricelist_uom_id desc, product_id desc, min_quantity desc, id desc',
            limit=1
        )
        
        if uom_specific_items:
            item = uom_specific_items[0]
            return self._calculate_item_price(item, product)
        
        general_items = self.env['product.pricelist.item'].search(
            domain + [
                '|', ('product_id', '=', product_id), ('product_tmpl_id', '=', product_tmpl_id),
                '|', ('pricelist_uom_id', '=', False), ('pricelist_uom_id', '=', None)
            ],
            order='product_id desc, min_quantity desc, id desc',
            limit=1
        )
        
        if general_items:
            item = general_items[0]
            return self._calculate_item_price(item, product)
        
        return 0.0
    
    def _calculate_item_price(self, item, product):
        if item.compute_price == 'fixed':
            return item.fixed_price
        elif item.compute_price == 'percentage':
            base_price = product.list_price
            return base_price * (1 - item.percent_price / 100)
        elif item.compute_price == 'formula':
            base_price = product.list_price
            return base_price + item.price_surcharge
        return product.list_price
class ProductProduct(models.Model):
    _inherit = 'product.product'
    
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

    @api.model
    def search_by_barcode(self, barcode, pricelist_id=None, quantity=1.0, date=None):
        if not barcode:
            return False
        
        barcode_uom_record = self.env['product.barcode.uom'].search([
            ('barcode', '=', barcode),
            ('active', '=', True)
        ], limit=1)
        
        if barcode_uom_record:
            product_variants = barcode_uom_record.product_id.product_variant_ids.filtered('active')
            if product_variants:
                product_variant = product_variants[0]
                final_price = barcode_uom_record.sale_price
                
                if pricelist_id:
                    pricelist = self.env['product.pricelist'].browse(pricelist_id)
                    if pricelist.exists():
                        pricelist_price = pricelist.get_pricelist_price_for_barcode(
                            product_variant.id, 
                            barcode_uom_record.uom_id.id, 
                            quantity, 
                            date
                        )
                        if pricelist_price > 0:
                            final_price = pricelist_price
                
                return {
                    'product_id': product_variant.id,
                    'product': product_variant,
                    'uom_id': barcode_uom_record.uom_id.id,
                    'uom': barcode_uom_record.uom_id,
                    'barcode_record': barcode_uom_record,
                    'price_unit': final_price,
                    'found_by': 'uom_barcode'
                }
        
        product = self.search(['|', ('barcode', '=', barcode), ('default_code', '=', barcode)], limit=1)
        if product:
            final_price = product.list_price
            
            if pricelist_id:
                pricelist = self.env['product.pricelist'].browse(pricelist_id)
                if pricelist.exists():
                    pricelist_price = pricelist.get_pricelist_price_for_barcode(
                        product.id, 
                        product.uom_id.id, 
                        quantity, 
                        date
                    )
                    if pricelist_price > 0:
                        final_price = pricelist_price
            
            return {
                'product_id': product.id,
                'product': product,
                'uom_id': product.uom_id.id,
                'uom': product.uom_id,
                'barcode_record': False,
                'price_unit': final_price,
                'found_by': 'standard_barcode'
            }
        
        return False
import logging
from odoo import models, fields, api

_logger = logging.getLogger(__name__)

class SaleOrder(models.Model):
    _inherit = 'sale.order'
    
    @api.onchange('pricelist_id')
    def _onchange_pricelist_id(self):
        result = super()._onchange_pricelist_id()
        for line in self.order_line:
            if line.barcode_uom_id:
                line.product_uom = line.barcode_uom_id.uom_id
                line.price_unit = line.barcode_uom_id.sale_price
            else:
                line._apply_pricing_logic()
        return result

class SaleOrderLine(models.Model):
    _inherit = 'sale.order.line'
    
    barcode_uom_id = fields.Many2one('product.barcode.uom', string='Barcode UoM Record')
    scanned_barcode = fields.Char(string='Scanned Barcode', help='Store the actual scanned barcode value')

    @api.onchange('product_id')
    def product_id_change(self):
        result = super().product_id_change()
        if self.product_id:
            if not self.barcode_uom_id:
                barcode_uom_records = self.env['product.barcode.uom'].search([
                    ('product_id', '=', self.product_id.product_tmpl_id.id),
                    ('active', '=', True)
                ])
                if barcode_uom_records:
                    barcode_uom_ids = barcode_uom_records.mapped('uom_id.id')
                    if self.product_id.uom_id.id not in barcode_uom_ids:
                        barcode_uom_ids.append(self.product_id.uom_id.id)
                    
                    selected_barcode_record = None
                    if self.scanned_barcode:
                        for record in barcode_uom_records:
                            if record.barcode == self.scanned_barcode:
                                selected_barcode_record = record
                                break
                    
                    if selected_barcode_record:
                        self.product_uom = selected_barcode_record.uom_id
                        self.barcode_uom_id = selected_barcode_record.id
                        self.price_unit = selected_barcode_record.sale_price
                    else:
                        selected_barcode_record = barcode_uom_records[0]
                        self.product_uom = selected_barcode_record.uom_id
                        self.barcode_uom_id = selected_barcode_record.id
                        self.price_unit = selected_barcode_record.sale_price
                    
                    default_uom_category = self.product_id.uom_id.category_id
                    same_category_uoms = self.env['uom.uom'].search([
                        ('category_id', '=', default_uom_category.id),
                        ('active', '=', True)
                    ])
                    all_allowed_uom_ids = list(set(barcode_uom_ids + same_category_uoms.ids))
                    
                    if result is None:
                        result = {}
                    if 'domain' not in result:
                        result['domain'] = {}
                    result['domain']['product_uom'] = [('id', 'in', all_allowed_uom_ids)]
                else:
                    default_uom_category = self.product_id.uom_id.category_id
                    same_category_uoms = self.env['uom.uom'].search([
                        ('category_id', '=', default_uom_category.id),
                        ('active', '=', True)
                    ])
                    if result is None:
                        result = {}
                    if 'domain' not in result:
                        result['domain'] = {}
                    result['domain']['product_uom'] = [('id', 'in', same_category_uoms.ids)]
            
            if not self.barcode_uom_id:
                self._apply_pricing_logic()
        return result

    @api.onchange('product_uom')
    def _onchange_product_uom(self):
        if self.product_id and self.product_uom:
            barcode_record = self.env['product.barcode.uom'].search([
                ('product_id', '=', self.product_id.product_tmpl_id.id),
                ('uom_id', '=', self.product_uom.id),
                ('active', '=', True)
            ], limit=1)
            
            if barcode_record:
                self.barcode_uom_id = barcode_record.id
                self.price_unit = barcode_record.sale_price
            else:
                self.barcode_uom_id = False
                self._apply_pricing_logic()

    @api.onchange('scanned_barcode')
    def _onchange_scanned_barcode(self):
        if self.scanned_barcode:
            barcode_record = self.env['product.barcode.uom'].search([
                ('barcode', '=', self.scanned_barcode),
                ('active', '=', True)
            ], limit=1)
            
            if barcode_record:
                product_variants = barcode_record.product_id.product_variant_ids.filtered('active')
                if product_variants:
                    self.product_id = product_variants[0]
                    self.barcode_uom_id = barcode_record.id
                    self.product_uom = barcode_record.uom_id
                    self.price_unit = barcode_record.sale_price
                    
                    _logger.info(f'Setting price for barcode {self.scanned_barcode}: UoM={barcode_record.uom_id.name}, Price={barcode_record.sale_price}')
                    
                    barcode_uom_records = self.env['product.barcode.uom'].search([
                        ('product_id', '=', barcode_record.product_id.id),
                        ('active', '=', True)
                    ])
                    barcode_uom_ids = barcode_uom_records.mapped('uom_id.id')
                    if self.product_id.uom_id.id not in barcode_uom_ids:
                        barcode_uom_ids.append(self.product_id.uom_id.id)
                    default_uom_category = self.product_id.uom_id.category_id
                    same_category_uoms = self.env['uom.uom'].search([
                        ('category_id', '=', default_uom_category.id),
                        ('active', '=', True)
                    ])
                    all_allowed_uom_ids = list(set(barcode_uom_ids + same_category_uoms.ids))
                    
                    return {
                        'domain': {
                            'product_uom': [('id', 'in', all_allowed_uom_ids)]
                        }
                    }
            else:
                product = self.env['product.product'].search([
                    ('barcode', '=', self.scanned_barcode),
                    ('active', '=', True)
                ], limit=1)
                
                if product:
                    self.product_id = product
                    self.product_uom = product.uom_id
                    self.barcode_uom_id = False
                    self._apply_pricing_logic()
                    
                    default_uom_category = product.uom_id.category_id
                    same_category_uoms = self.env['uom.uom'].search([
                        ('category_id', '=', default_uom_category.id),
                        ('active', '=', True)
                    ])
                    
                    return {
                        'domain': {
                            'product_uom': [('id', 'in', same_category_uoms.ids)]
                        }
                    }

    def _sync_barcode_uom_data(self):
        if self.barcode_uom_id:
            try:
                self.product_uom = self.barcode_uom_id.uom_id
                self.price_unit = self.barcode_uom_id.sale_price
            except Exception as e:
                _logger.warning(f'Error syncing barcode UoM data: {str(e)}')
                self._apply_pricing_logic()

    def _apply_pricing_logic(self):
        if not self.product_id:
            return
            
        try:
            new_price = None
            
            if self.barcode_uom_id:
                new_price = self.barcode_uom_id.sale_price
                if new_price and new_price > 0:
                    self.price_unit = new_price
                    return
                else:
                    _logger.warning(f'Barcode UoM has invalid sale_price: {new_price}')
            
            promotion_price = self._check_promotion_code()
            if promotion_price is not None:
                new_price = promotion_price
            
            if new_price is None:
                pricelist_price = self._check_pricelist_conditions()
                if pricelist_price is not None:
                    new_price = pricelist_price
            
            if new_price is None:
                new_price = self._get_fallback_sales_price()
            
            self.price_unit = new_price
                        
        except Exception as e:
            _logger.error(f'Error applying pricing logic: {str(e)}')
            self.price_unit = self._get_fallback_sales_price()

    def _check_promotion_code(self):
        if not self.product_id or not self.order_id:
            return None
            
        try:
            order_date = self.order_id.date_order
            if hasattr(order_date, 'date'):
                order_date = order_date.date()
            elif not order_date:
                order_date = fields.Date.today()
            
            quantity = self.product_uom_qty or 1.0
            
            domain = [
                ('product_id', '=', self.product_id.product_tmpl_id.id),
                ('active', '=', True),
                ('date_from', '<=', order_date),
                ('date_to', '>=', order_date),
                ('min_quantity', '<=', quantity)
            ]
            
            if self.product_uom:
                domain.append(('uom_id', '=', self.product_uom.id))
            promotion_records = self.env['product.promotion'].search(
                domain, 
                order='sequence, min_quantity desc, id', 
                limit=1
            )
            
            if promotion_records:
                _logger.info(f'Found promotion for product {self.product_id.name}: Price {promotion_records[0].promotion_price}')
                return promotion_records[0].promotion_price
                
        except Exception as e:
            _logger.warning(f'Error checking promotion code: {str(e)}')
            
        return None

    def _check_pricelist_conditions(self):
        if not (self.order_id and self.order_id.pricelist_id and self.product_id):
            return None
            
        try:
            order_date = self.order_id.date_order
            if hasattr(order_date, 'date'):
                order_date = order_date.date()
            elif not order_date:
                order_date = fields.Date.today()
            quantity = self.product_uom_qty or 1.0
            pricelist = self.order_id.pricelist_id
            
            domain = [
                ('pricelist_id', '=', pricelist.id),
                ('product_tmpl_id', '=', self.product_id.product_tmpl_id.id),
            ]
            if self.product_uom:
                domain.append(('uom_id', '=', self.product_uom.id))
            
            pricelist_items = self.env['product.pricelist.item'].search(domain)
            
            if pricelist_items:
                for item in pricelist_items:
                    date_valid = True
                    
                    if item.date_start and item.date_start > order_date:
                        date_valid = False
                        continue
                    if item.date_end and item.date_end < order_date:
                        date_valid = False
                        continue
                        
                    quantity_valid = quantity >= item.min_quantity
                    if not quantity_valid:
                        continue
                    
                    if date_valid and quantity_valid:
                        base_price = self.product_id.list_price
                        
                        if item.compute_price == 'fixed':
                            calculated_price = item.fixed_price
                        elif item.compute_price == 'percentage':
                            calculated_price = base_price * (1 - item.percent_price / 100)
                        elif item.compute_price == 'formula':
                            calculated_price = base_price + item.price_surcharge
                        else:
                            calculated_price = base_price
                        
                        return calculated_price
                
                return self._check_price_rules()
            else:
                return self._check_price_rules()
                    
        except Exception as e:
            _logger.warning(f'Error checking pricelist conditions: {str(e)}')
            
        return None

    def _check_price_rules(self):
        if not (self.order_id and self.product_id):
            return None
            
        try:
            order_date = self.order_id.date_order
            if hasattr(order_date, 'date'):
                order_date = order_date.date()
            elif not order_date:
                order_date = fields.Date.today()
            quantity = self.product_uom_qty or 1.0
            
            domain = [
                ('product_id', '=', self.product_id.product_tmpl_id.id),
                ('active', '=', True),
                ('date_from', '<=', order_date),
                ('date_to', '>=', order_date),
                ('min_quantity', '<=', quantity)
            ]
            
            if self.product_uom:
                domain.append(('uom_id', '=', self.product_uom.id))
            price_rules = self.env['product.price.rule'].search(
                domain, 
                order='sequence, min_quantity desc, id', 
                limit=1
            )
            
            if price_rules:
                return price_rules[0].price
                
        except Exception as e:
            _logger.warning(f'Error checking price rules: {str(e)}')
            
        return None

    def _get_barcode_uom_sale_price(self):
        if not self.barcode_uom_id:
            return None
            
        try:
            price = self.barcode_uom_id.sale_price
            if price and price > 0:
                return price
            else:
                _logger.warning(f'Barcode UoM has invalid sale_price: {price}')
                return None
        except Exception as e:
            _logger.warning(f'Error getting barcode UoM sale price: {str(e)}')
            
        return None

    def _get_fallback_sales_price(self):
        if not self.product_id:
            return 0.0
            
        try:
            fallback_price = self.product_id.list_price or 0.0
            return fallback_price
        except Exception as e:
            _logger.warning(f'Error getting fallback sales price: {str(e)}')
            return 0.0

    def _update_price_from_barcode(self, barcode_record):
        self.product_uom = barcode_record.uom_id
        self.price_unit = barcode_record.sale_price

    def _update_standard_price(self):
        self._apply_pricing_logic()

    @api.model
    def create(self, vals):
        if 'scanned_barcode' in vals and vals['scanned_barcode']:
            barcode_record = self.env['product.barcode.uom'].search([
                ('barcode', '=', vals['scanned_barcode']),
                ('active', '=', True)
            ], limit=1)
            
            if barcode_record:
                vals['barcode_uom_id'] = barcode_record.id
                vals['product_uom'] = barcode_record.uom_id.id
                vals['price_unit'] = barcode_record.sale_price
        
        record = super().create(vals)
        
        if record.barcode_uom_id:
            record.product_uom = record.barcode_uom_id.uom_id
            record.price_unit = record.barcode_uom_id.sale_price
        elif record.product_id:
            record._apply_pricing_logic()
        
        return record

    def write(self, vals):
        result = super().write(vals)
        
        if 'scanned_barcode' in vals and vals['scanned_barcode']:
            for record in self:
                barcode_record = self.env['product.barcode.uom'].search([
                    ('barcode', '=', vals['scanned_barcode']),
                    ('active', '=', True)
                ], limit=1)
                
                if barcode_record:
                    record.barcode_uom_id = barcode_record.id
                    record.product_uom = barcode_record.uom_id
                    record.price_unit = barcode_record.sale_price
        
        if any(field in vals for field in ['barcode_uom_id', 'product_id', 'product_uom', 'product_uom_qty', 'scanned_barcode']):
            for record in self:
                if record.barcode_uom_id:
                    record.product_uom = record.barcode_uom_id.uom_id
                    record.price_unit = record.barcode_uom_id.sale_price
                elif record.product_id:
                    record._apply_pricing_logic()
        
        return result

    @api.onchange('barcode_uom_id')
    def _onchange_barcode_uom_id(self):
        if self.barcode_uom_id:
            product_variants = self.barcode_uom_id.product_id.product_variant_ids.filtered('active')
            if product_variants:
                self.product_id = product_variants[0]
            self.product_uom = self.barcode_uom_id.uom_id
            self.price_unit = self.barcode_uom_id.sale_price
        else:
            if self.product_id:
                self.product_uom = self.product_id.uom_id
                self._apply_pricing_logic()

    @api.onchange('product_uom_qty')
    def _onchange_product_uom_qty(self):
        result = super()._onchange_product_uom_qty()
        
        if self.product_id:
            if self.barcode_uom_id:
                self.price_unit = self.barcode_uom_id.sale_price
            else:
                self._apply_pricing_logic()
        
        return result

class ProductTemplate(models.Model):
    _inherit = 'product.template'
    
    barcode_uom_ids = fields.One2many('product.barcode.uom', 'product_id', string="Barcode UoMs")
    barcode_count = fields.Integer(string="Barcode Count", compute='_compute_barcode_count', store=True)
    uom_category_id = fields.Many2one('uom.category', string='UoM Category', help='Filter available UoMs by category')
    
    @api.depends('barcode_uom_ids', 'barcode_uom_ids.active')
    def _compute_barcode_count(self):
        for record in self:
            record.barcode_count = len(record.barcode_uom_ids.filtered('active'))
    
    def action_view_barcodes(self):
        self.ensure_one()
        action = {
            'name': 'Product Barcodes',
            'type': 'ir.actions.act_window',
            'res_model': 'product.barcode.uom',
            'view_mode': 'tree,form',
            'domain': [('product_id', '=', self.id)],
            'context': {
                'default_product_id': self.id,
                'search_default_product_id': self.id,
                'default_uom_category_id': self.uom_category_id.id if self.uom_category_id else False,
            },
        }
        return action
    
    @api.model
    def name_search(self, name='', args=None, operator='ilike', limit=100):
        if args is None:
            args = []
        result = super().name_search(name, args, operator, limit)
        if name and len(result) < limit:
            barcode_records = self.env['product.barcode.uom'].search([
                ('barcode', operator, name),
                ('active', '=', True)
            ], limit=limit - len(result))
            
            existing_ids = [r[0] for r in result]
            for barcode_rec in barcode_records:
                if barcode_rec.product_id.id not in existing_ids:
                    result.append((barcode_rec.product_id.id,
                                  f"{barcode_rec.product_id.name} [{barcode_rec.barcode}] - {barcode_rec.uom_id.name}"))
        
        return result
class PurchaseOrderLine(models.Model):
    _inherit = 'purchase.order.line'
    
    barcode_uom_id = fields.Many2one('product.barcode.uom', string='Barcode UoM Record')
    
    @api.model
    def create(self, vals):
        if 'barcode_uom_id' in vals and vals['barcode_uom_id']:
            barcode_record = self.env['product.barcode.uom'].browse(vals['barcode_uom_id'])
            if barcode_record.exists():
                product_variants = barcode_record.product_id.product_variant_ids.filtered('active')
                if product_variants:
                    vals['product_id'] = product_variants[0].id
                    vals['product_uom'] = barcode_record.uom_id.id
        
        return super().create(vals)
    
    def write(self, vals):
        if 'barcode_uom_id' in vals:
            for line in self:
                if vals['barcode_uom_id']:
                    barcode_record = self.env['product.barcode.uom'].browse(vals['barcode_uom_id'])
                    if barcode_record.exists():
                        product_variants = barcode_record.product_id.product_variant_ids.filtered('active')
                        if product_variants:
                            vals['product_id'] = product_variants[0].id
                            vals['product_uom'] = barcode_record.uom_id.id
        
        return super().write(vals)
    
    @api.onchange('barcode_uom_id')
    def _onchange_barcode_uom_id(self):
        if self.barcode_uom_id:
            product_variants = self.barcode_uom_id.product_id.product_variant_ids.filtered('active')
            if product_variants:
                self.product_id = product_variants[0]
                self.product_uom = self.barcode_uom_id.uom_id
    
    @api.onchange('product_id')
    def onchange_product_id(self):
        if not self.barcode_uom_id:
            result = super().onchange_product_id()
            return result
        else:
            if self.barcode_uom_id and self.barcode_uom_id.uom_id:
                old_uom = self.product_uom
                result = super().onchange_product_id()
                self.product_uom = self.barcode_uom_id.uom_id
                return result
            else:
                result = super().onchange_product_id()
                return result


class StockMoveLine(models.Model):
    _inherit = 'stock.move.line'
    
    barcode_uom_id = fields.Many2one('product.barcode.uom', string='Barcode UoM Record')
    
    @api.model
    def create(self, vals):
        if 'barcode_uom_id' in vals and vals['barcode_uom_id']:
            barcode_record = self.env['product.barcode.uom'].browse(vals['barcode_uom_id'])
            if barcode_record.exists():
                product_variants = barcode_record.product_id.product_variant_ids.filtered('active')
                if product_variants:
                    vals['product_id'] = product_variants[0].id
                    vals['product_uom_id'] = barcode_record.uom_id.id
        
        return super().create(vals)
    
    def write(self, vals):
        if 'barcode_uom_id' in vals:
            for line in self:
                if vals['barcode_uom_id']:
                    barcode_record = self.env['product.barcode.uom'].browse(vals['barcode_uom_id'])
                    if barcode_record.exists():
                        product_variants = barcode_record.product_id.product_variant_ids.filtered('active')
                        if product_variants:
                            vals['product_id'] = product_variants[0].id
                            vals['product_uom_id'] = barcode_record.uom_id.id
        
        return super().write(vals)
    
    @api.onchange('barcode_uom_id')
    def _onchange_barcode_uom_id(self):
        if self.barcode_uom_id:
            product_variants = self.barcode_uom_id.product_id.product_variant_ids.filtered('active')
            if product_variants:
                self.product_id = product_variants[0]
                self.product_uom_id = self.barcode_uom_id.uom_id


class PosOrderLine(models.Model):
    _inherit = 'pos.order.line'
    
    barcode_uom_id = fields.Many2one('product.barcode.uom', string='Barcode UoM Record')
    
    @api.model
    def create(self, vals):
        if 'barcode_uom_id' in vals and vals['barcode_uom_id']:
            barcode_record = self.env['product.barcode.uom'].browse(vals['barcode_uom_id'])
            if barcode_record.exists():
                product_variants = barcode_record.product_id.product_variant_ids.filtered('active')
                if product_variants:
                    vals['product_id'] = product_variants[0].id
                    vals['uom_id'] = barcode_record.uom_id.id
                    
                    if 'order_id' in vals and vals['order_id']:
                        order = self.env['pos.order'].browse(vals['order_id'])
                        if order.exists() and order.pricelist_id:
                            pricelist_id = order.pricelist_id.id
                            
                            barcode_data = self.env['product.product'].search_by_barcode(
                                barcode_record.barcode,
                                pricelist_id,
                                vals.get('qty', 1.0),
                                fields.Date.today()
                            )
                            
                            if barcode_data and 'price_unit' not in vals:
                                vals['price_unit'] = barcode_data['price_unit']
        
        return super().create(vals)
    
    def write(self, vals):
        if 'barcode_uom_id' in vals:
            for line in self:
                if vals['barcode_uom_id']:
                    barcode_record = self.env['product.barcode.uom'].browse(vals['barcode_uom_id'])
                    if barcode_record.exists():
                        product_variants = barcode_record.product_id.product_variant_ids.filtered('active')
                        if product_variants:
                            vals['product_id'] = product_variants[0].id
                            vals['uom_id'] = barcode_record.uom_id.id
                            
                            if line.order_id and line.order_id.pricelist_id:
                                pricelist_id = line.order_id.pricelist_id.id
                                
                                barcode_data = self.env['product.product'].search_by_barcode(
                                    barcode_record.barcode,
                                    pricelist_id,
                                    line.qty or 1.0,
                                    fields.Date.today()
                                )
                                
                                if barcode_data:
                                    vals['price_unit'] = barcode_data['price_unit']
        
        return super().write(vals)
    
    @api.onchange('barcode_uom_id')
    def _onchange_barcode_uom_id(self):
        if self.barcode_uom_id:
            product_variants = self.barcode_uom_id.product_id.product_variant_ids.filtered('active')
            if product_variants:
                self.product_id = product_variants[0]
                self.uom_id = self.barcode_uom_id.uom_id
                
                if self.order_id and self.order_id.pricelist_id:
                    pricelist_id = self.order_id.pricelist_id.id
                    
                    barcode_data = self.env['product.product'].search_by_barcode(
                        self.barcode_uom_id.barcode,
                        pricelist_id,
                        self.qty or 1.0,
                        fields.Date.today()
                    )
                    
                    if barcode_data:
                        self.price_unit = barcode_data['price_unit']


class StockMove(models.Model):
    _inherit = 'stock.move'
    
    barcode_uom_id = fields.Many2one('product.barcode.uom', string='Barcode UoM Record')
    
    @api.model
    def create(self, vals):
        if 'barcode_uom_id' in vals and vals['barcode_uom_id']:
            barcode_record = self.env['product.barcode.uom'].browse(vals['barcode_uom_id'])
            if barcode_record.exists():
                product_variants = barcode_record.product_id.product_variant_ids.filtered('active')
                if product_variants:
                    vals['product_id'] = product_variants[0].id
                    vals['product_uom'] = barcode_record.uom_id.id
        
        return super().create(vals)
    
    def write(self, vals):
        if 'barcode_uom_id' in vals:
            for move in self:
                if vals['barcode_uom_id']:
                    barcode_record = self.env['product.barcode.uom'].browse(vals['barcode_uom_id'])
                    if barcode_record.exists():
                        product_variants = barcode_record.product_id.product_variant_ids.filtered('active')
                        if product_variants:
                            vals['product_id'] = product_variants[0].id
                            vals['product_uom'] = barcode_record.uom_id.id
        
        return super().write(vals)
    
    @api.onchange('barcode_uom_id')
    def _onchange_barcode_uom_id(self):
        if self.barcode_uom_id:
            product_variants = self.barcode_uom_id.product_id.product_variant_ids.filtered('active')
            if product_variants:
                self.product_id = product_variants[0]
                self.product_uom = self.barcode_uom_id.uom_id


class AccountMoveLine(models.Model):
    _inherit = 'account.move.line'
    
    barcode_uom_id = fields.Many2one('product.barcode.uom', string='Barcode UoM Record')
    
    @api.model
    def create(self, vals):
        if 'barcode_uom_id' in vals and vals['barcode_uom_id']:
            barcode_record = self.env['product.barcode.uom'].browse(vals['barcode_uom_id'])
            if barcode_record.exists():
                product_variants = barcode_record.product_id.product_variant_ids.filtered('active')
                if product_variants:
                    vals['product_id'] = product_variants[0].id
                    vals['product_uom_id'] = barcode_record.uom_id.id
        
        return super().create(vals)
    
    def write(self, vals):
        if 'barcode_uom_id' in vals:
            for line in self:
                if vals['barcode_uom_id']:
                    barcode_record = self.env['product.barcode.uom'].browse(vals['barcode_uom_id'])
                    if barcode_record.exists():
                        product_variants = barcode_record.product_id.product_variant_ids.filtered('active')
                        if product_variants:
                            vals['product_id'] = product_variants[0].id
                            vals['product_uom_id'] = barcode_record.uom_id.id
        
        return super().write(vals)
    
    @api.onchange('barcode_uom_id')
    def _onchange_barcode_uom_id(self):
        if self.barcode_uom_id:
            product_variants = self.barcode_uom_id.product_id.product_variant_ids.filtered('active')
            if product_variants:
                self.product_id = product_variants[0]
                self.product_uom_id = self.barcode_uom_id.uom_id