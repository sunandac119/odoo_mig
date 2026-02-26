from odoo import models, fields, api, _
from odoo.exceptions import UserError, ValidationError
from datetime import date

import logging

_logger = logging.getLogger(__name__)


class ProductPricelist(models.Model):
    _inherit = 'product.pricelist'

    def action_product_pricelist(self):
        """Update pricelist items and log changes."""
        try:
            Param = self.env['ir.config_parameter'].sudo()
            batch_size = 10
            last_offset = int(Param.get_param('uom_update_last_offset') or 0)

            products = self.env['product.pricelist'].search([], offset=last_offset, limit=batch_size)

            if not products:
                last_offset = 0
                products = self.env['product.pricelist'].search([], offset=last_offset, limit=batch_size)

            if not products:
                return

            product_ids = tuple(products.ids)
            start_num = last_offset + 1
            end_num = last_offset + len(product_ids)

            for pricelist in products:

                for item in pricelist.item_ids:
                    tmpl = item.product_tmpl_id

                    if not tmpl.active:
                        _logger.warning(
                            "Skipping item ID %s — Product Template inactive or missing (Template ID: %s).",
                            item.id, tmpl.id if tmpl else 'N/A'
                        )
                        continue

                    barcode = tmpl.barcode
                    uom = tmpl.uom_id

                    if tmpl.barcode_uom_ids and item.x_scanned_barcode:
                        match_found = False
                        for line in tmpl.barcode_uom_ids:
                            if line.barcode == item.x_scanned_barcode:
                                barcode = line.barcode
                                uom = line.uom_id
                                match_found = True
                                break
                        if not match_found:
                            _logger.warning("Barcode %s not found in Product Barcode UOM for %s (Template ID: %s)", 
                                            item.x_scanned_barcode, tmpl.name, tmpl.id)

                    item.write({
                        'x_scanned_barcode': barcode,
                        'uom_id': uom.id if uom else False,
                    })

                    if tmpl.parent_template_id and tmpl.id != tmpl.parent_template_id.id and tmpl.active:
                        item.product_tmpl_id = tmpl.parent_template_id

            total_products = self.env['product.pricelist'].search_count([])
            new_offset = last_offset + batch_size
            if new_offset >= total_products:
                new_offset = 0
            Param.set_param('uom_update_last_offset', str(new_offset))

        except Exception as e:
            _logger.error("Error updating PO/SO UOM history: %s", str(e))
            raise ValidationError(_("Server action failed: %s") % str(e))

            return True
    # def action_product_pricelist(self):
    #     """Update pricelist items and log changes."""
    #     try:
    #         Param = self.env['ir.config_parameter'].sudo()
    #         batch_size = 10

    #         # Get last offset, default 0
    #         last_offset = int(Param.get_param('uom_update_last_offset') or 0)

    #         # Fetch next batch of products
    #         products = self.env['product.pricelist'].search([], offset=last_offset, limit=batch_size)
    #         if not products:
    #             last_offset = 0
    #             products = self.env['product.pricelist'].search([], offset=last_offset, limit=batch_size)

    #         if not products:
    #             _logger.info("No product pricelist found for update.")
    #             return

    #         product_ids = tuple(products.ids)
    #         start_num = last_offset + 1
    #         end_num = last_offset + len(product_ids)

    #         for pricelist in products:
    #             _logger.info("Updating Pricelist: %s (ID: %s)", pricelist.name, pricelist.id)
    #             for item in pricelist.item_ids:
    #                 tmpl = item.product_tmpl_id  # define once for both branches
    #                 barcode = tmpl.barcode       # default values
    #                 uom = tmpl.uom_id

    #                 if tmpl.barcode_uom_ids and item.x_scanned_barcode:
    #                     # Pick the matching barcode_uom_id if found
    #                     for line in tmpl.barcode_uom_ids:
    #                         if line.barcode == item.x_scanned_barcode:
    #                             barcode = line.barcode
    #                             uom = line.uom_id
    #                             break  # no need to keep looping

    #                 item.write({
    #                     'x_scanned_barcode': barcode,
    #                     'uom_id': uom.id if uom else False,
    #                 })

    #                 if tmpl.parent_template_id and tmpl.id != tmpl.parent_template_id.id and tmpl.active:
    #                     item.product_tmpl_id = tmpl.parent_template_id
                        
    #         # Update offset
    #         total_products = self.env['product.pricelist'].search_count([])
    #         new_offset = last_offset + batch_size
    #         if new_offset >= total_products:
    #             new_offset = 0
    #         Param.set_param('uom_update_last_offset', str(new_offset))
    #         _logger.info("Updated offset to %s for next batch", new_offset)

    #     except Exception as e:
    #         _logger.error("Error updating PO/SO UOM history: %s", str(e))
    #         raise ValidationError(_("Server action failed: %s") % str(e))

    #         return True

    def action_delete_expired_rules(self):
        pricelists = self.env['product.pricelist'].search([])
        now = fields.Datetime.now()
        for pricelist in pricelists:
            expired_items = pricelist.item_ids.filtered(
                lambda l: l.date_end and l.date_end < now
            )
            if expired_items:
                expired_items.unlink()


class ProductPricelistItem(models.Model):
    _inherit = "product.pricelist.item"

    @api.model
    def create(self, vals):
        _logger.info("Product Price Rule Create")
        barcode = vals.get('x_scanned_barcode')
        if barcode:
            barcode_line = self.env['product.barcode.uom'].search([('barcode', '=', barcode)], limit=1)
            if barcode_line:
                vals['uom_id'] = barcode_line.uom_id.id
            else:
                _logger.info("Barcode %s not found in Product Barcode UOM", barcode)
                ''' Replaced the usererror to log because getting issue from this usererror while executing
                    the server action in price list
                '''
                # raise UserError(_('Barcode %s not found in Product Barcode UOM') % barcode)
        return super().create(vals)

    def write(self, vals):
        _logger.info("Product Price Rule Write")
        barcode = vals.get('x_scanned_barcode')
        if barcode:
            barcode_line = self.env['product.barcode.uom'].search([('barcode', '=', barcode)], limit=1)
            if barcode_line:
                vals['uom_id'] = barcode_line.uom_id.id
            else:
                _logger.info("Barcode %s not found in Product Barcode UOM", barcode)
                ''' Replaced the usererror to log because getting issue from this usererror while executing
                    the server action in price list
                '''
                # raise UserError(_('Barcode %s not found in Product Barcode UOM') % barcode)
        return super().write(vals)
        
    @api.model
    def cron_delete_expired_pricelist_items(self):
        today = date.today()
        expired_items = self.search([('date_end', '<', today)])
        if expired_items:
            expired_items.unlink()


