from odoo import models, fields, api
from datetime import datetime, date
import logging

_logger = logging.getLogger(__name__)


class SaleOrderLine(models.Model):
    _inherit = 'sale.order.line'

    x_scanned_barcode = fields.Char(string="Scanned Barcode")
    _barcode_price_override = fields.Float(string="Barcode Price Override", store=False)
    _skip_pricelist_computation = fields.Boolean(string="Skip Pricelist", store=False, default=False)

    @api.onchange('x_scanned_barcode')
    def _onchange_x_scanned_barcode(self):
        if not self.x_scanned_barcode:
            self._barcode_price_override = 0.0
            self._skip_pricelist_computation = False
            return

        _logger.info(f"=== PROCESSING BARCODE: {self.x_scanned_barcode} ===")

        # Search directly in f.pos.multi.uom.barcode.lines
        barcode_line = self.env['f.pos.multi.uom.barcode.lines'].search([
            ('barcode', '=', self.x_scanned_barcode)
        ], limit=1)

        if barcode_line:
            _logger.info(f"=== FOUND BARCODE LINE ===")
            _logger.info(f"Product template: {barcode_line.uom_barcode.name}")
            _logger.info(f"UOM: {barcode_line.uom.name} (ID: {barcode_line.uom.id})")
            _logger.info(f"Sale price: {barcode_line.sale_price}")

            # Find product variant
            product = self.env['product.product'].search([
                ('product_tmpl_id', '=', barcode_line.uom_barcode.id)
            ], limit=1)

            if product:
                _logger.info(f"=== SETTING FIELDS ===")

                # Calculate price with priority logic including date range
                final_price = self._get_price_from_pricelist_or_barcode(product, barcode_line)

                # Store the price override to use later
                self._barcode_price_override = final_price
                self._skip_pricelist_computation = True

                # Set product first
                self.product_id = product.id

                # Set UOM from barcode line
                self.product_uom = barcode_line.uom.id

                # Set quantity if not set
                if not self.product_uom_qty:
                    self.product_uom_qty = 1.0

                # Set price directly
                self.price_unit = final_price

                _logger.info(
                    f"=== FIELDS SET: Product={product.name}, UOM={barcode_line.uom.name}, Price={final_price} ===")

            else:
                _logger.error(f"=== NO PRODUCT VARIANT FOUND ===")

        else:
            _logger.info(f"=== NO MULTI-UOM BARCODE FOUND ===")
            self._barcode_price_override = 0.0
            self._skip_pricelist_computation = False

    @api.onchange('product_id')
    def product_id_change(self):
        """Override product_id_change to handle barcode scenarios"""

        # If we have an active barcode with override price, handle it specially
        if self.x_scanned_barcode and self._barcode_price_override > 0 and self._skip_pricelist_computation:
            _logger.info(f"=== SKIPPING STANDARD PRODUCT ONCHANGE FOR BARCODE ===")

            # Just set the product name, don't change price or UOM
            if self.product_id and not self.name:
                self.name = self.product_id.display_name

            return

        # For normal cases, call the standard onchange if product exists
        if self.product_id:
            try:
                result = super().product_id_change()
                return result
            except AttributeError:
                # If method doesn't exist, just set basic values
                if not self.name:
                    self.name = self.product_id.display_name
                if not self.product_uom:
                    self.product_uom = self.product_id.uom_id.id

    @api.onchange('product_id', 'product_uom_qty', 'product_uom', 'pricelist_id')
    def _onchange_product_override(self):
        """Override to control price after product selection"""

        # Store current values before any changes
        current_barcode = self.x_scanned_barcode
        override_price = self._barcode_price_override
        skip_pricelist = self._skip_pricelist_computation

        _logger.info(f"=== PRODUCT OVERRIDE ONCHANGE ===")
        _logger.info(f"Barcode: {current_barcode}")
        _logger.info(f"Override price: {override_price}")
        _logger.info(f"Skip pricelist: {skip_pricelist}")

        # If we have a barcode active with skip flag, maintain our values
        if current_barcode and override_price > 0 and skip_pricelist:
            # Find the barcode line to get correct UOM
            barcode_line = self.env['f.pos.multi.uom.barcode.lines'].search([
                ('barcode', '=', current_barcode)
            ], limit=1)

            if barcode_line and self.product_id:
                _logger.info(f"=== MAINTAINING BARCODE VALUES ===")

                # Set product description if needed
                if not self.name:
                    self.name = self.product_id.display_name

                # Keep our custom values
                self.product_uom = barcode_line.uom.id
                self.price_unit = override_price

                _logger.info(f"=== MAINTAINED: UOM={barcode_line.uom.name}, Price={override_price} ===")

                return  # Don't call any other onchange

        # For normal cases, let Odoo handle standard logic

    def _get_price_from_pricelist_or_barcode(self, product, barcode_line):
        """
        Get price with priority:
        1. From pricelist if valid date range
        2. From POS UoM barcode line sale price
        3. From product default price
        """
        pricelist = self.order_id.pricelist_id
        partner = self.order_id.partner_id
        uom = barcode_line.uom
        qty = self.product_uom_qty or 1.0

        # Get current date from sale order or today's date
        current_date = self.order_id.date_order.date() if self.order_id.date_order else date.today()

        _logger.info(f"=== CALCULATING PRICE ===")
        _logger.info(f"Pricelist: {pricelist.name if pricelist else 'None'}")
        _logger.info(f"UOM: {uom.name}")
        _logger.info(f"Quantity: {qty}")
        _logger.info(f"Current Date: {current_date}")

        if pricelist:
            # Get all pricelist items for this product and UOM
            pricelist_items = self.env['product.pricelist.item'].search([
                ('pricelist_id', '=', pricelist.id),
                ('product_tmpl_id', '=', product.product_tmpl_id.id),
                ('product_id', 'in', [False, product.id]),
                '|',
                ('uom_id', '=', False),
                ('uom_id', '=', uom.id)
            ])

            _logger.info(f"Found total pricelist items: {len(pricelist_items)}")

            # Check each item for date validity
            valid_items = []
            for item in pricelist_items:
                is_valid = self._is_pricelist_item_valid_for_date(item, current_date)
                _logger.info(f"Item ID={item.id}, Start={item.date_start}, End={item.date_end}, Valid={is_valid}")
                if is_valid:
                    valid_items.append(item)

            _logger.info(f"Found {len(valid_items)} valid pricelist items for date {current_date}")

            if valid_items:
                # Use the first valid item (you can add more sorting logic if needed)
                matching_item = valid_items[0]
                _logger.info(f"Using pricelist item: ID={matching_item.id}, Price={matching_item.fixed_price}")

                try:
                    if matching_item.compute_price == 'fixed' and matching_item.fixed_price > 0:
                        _logger.info(f"Using pricelist price: {matching_item.fixed_price}")
                        return matching_item.fixed_price
                except Exception as e:
                    _logger.warning(f"Error getting pricelist price: {e}")
            else:
                _logger.info(f"No valid pricelist items found - will use barcode price")

        # Fallback to barcode line sale price
        if barcode_line.sale_price and barcode_line.sale_price > 0:
            _logger.info(f"Using barcode line price: {barcode_line.sale_price}")
            return barcode_line.sale_price

        # Final fallback to product price
        product_price = product.lst_price or 0.0
        _logger.info(f"Using product default price: {product_price}")
        return product_price

    def _is_pricelist_item_valid_for_date(self, pricelist_item, check_date):
        """
        Check if pricelist item is valid for the given date
        """
        if not check_date:
            return False

        # Convert to date objects if they are datetime objects
        if isinstance(check_date, datetime):
            check_date = check_date.date()

        start_date = pricelist_item.date_start
        end_date = pricelist_item.date_end

        if isinstance(start_date, datetime):
            start_date = start_date.date()
        if isinstance(end_date, datetime):
            end_date = end_date.date()

        # If no start date and no end date, it's always valid
        if not start_date and not end_date:
            return True

        # If only start date exists, check if current date is >= start date
        if start_date and not end_date:
            return check_date >= start_date

        # If only end date exists, check if current date is <= end date
        if not start_date and end_date:
            return check_date <= end_date

        # If both dates exist, check if current date is within range
        if start_date and end_date:
            is_valid = start_date <= check_date <= end_date
            _logger.info(f"Date range check: {start_date} <= {check_date} <= {end_date} = {is_valid}")
            return is_valid

        return False

    # Remove the problematic _compute_price_unit override for now
    # We'll handle price setting directly in onchange methods


# Also inherit the mixin to ensure it's available
class BarcodeLookup(models.AbstractModel):
    _inherit = 'multi.uom.barcode.lookup.mixin'