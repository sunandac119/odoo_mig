from odoo import api, fields, models, _
from odoo.tools import float_round
from datetime import datetime

class ProductProduct(models.Model):
    _inherit = "product.template"

    # @api.model
    # def get_product_details(self, barcode):
    #     # product = self.env['product.template'].sudo().search([('barcode_uom_ids.barcode', '=', barcode)], limit=1)
    #     product = self.env['product.product'].search([('barcode', '=', barcode)], limit=1)
    #     if not product:
    #         return {'error': 'Product not found for the given barcode.'}

    #     product_template = product
    #     today = fields.Date.context_today(self)

    #     vals = {
    #         'product_id': product.id,
    #         'product_name': product.name,
    #         'product_description_sale': product.description_sale,
    #         'product_barcode': product.barcode,
    #         'product_code': product.default_code,
    #         'product_currency_id': product.currency_id.symbol,
    #         'product_uom_id': product.uom_id.name,
    #         'product_price': float_round(product.list_price, precision_digits=2),  # Format to 2 decimal places
    #         'product_pricelists': [],
    #     }

    #     pricelists_data = []
    #     pricelists = self.env['product.pricelist'].search([])
    #     for pricelist in pricelists:
    #         items = []
    #         pricelist_items = product_template.fixed_pricelist_item_ids.filtered(
    #             lambda item: item.pricelist_id == pricelist and 
    #                          (not item.date_end or item.date_end.date() > today)  # Ensure both are dates
    #         )
    #         for pricelist_item in pricelist_items:
    #             if pricelist_item.compute_price == 'fixed':
    #                 price = pricelist_item.fixed_price
    #             else:
    #                 price = product.list_price - (product.list_price * (pricelist_item.percent_price / 100.0))
    #             # Ensure price is formatted to 2 decimal places
    #             price = float_round(price, precision_digits=2)
    #             items.append({
    #                 'pricelist_name': pricelist.name,
    #                 'price': price,
    #                 'date_end': pricelist_item.date_end.strftime('%Y-%m-%d') if pricelist_item.date_end else None,
    #             })
    #         if items:
    #             pricelists_data.append({
    #                 'pricelist_id': pricelist.id,
    #                 'pricelist_name': pricelist.name,
    #                 'items': items,
    #             })

    #     vals['product_pricelists'] = pricelists_data
    #     return vals

    @api.model
    def get_product_details(self, barcode):
        # product = self.env['product.template'].sudo().search([('barcode_uom_ids.barcode', '=', barcode)], limit=1)
        today = fields.Date.context_today(self)
        product = self.env['product.product'].search([('barcode', '=', barcode)], limit=1)
        if product:
            product_template = product
            uom_id = product.uom_id.id
            vals = {
                'product_id': product.id,
                'product_name': product.name,
                'product_description_sale': product.description_sale,
                'product_barcode': product.barcode,
                'product_code': product.default_code,
                'product_currency_id': product.currency_id.symbol,
                'product_uom_id': product.uom_id.name,
                'product_price': float_round(product.list_price, precision_digits=2),  # Format to 2 decimal places
                'product_pricelists': [],
            }
        else:
            line_product = self.env['product.barcode.uom'].search([('barcode', '=', barcode)], limit=1)
            if line_product:
                product_template = line_product.product_id
                uom_id = line_product.uom_id.id
                vals = {
                    'product_id': product_template.id,
                    'product_name': line_product.description,
                    'product_description_sale': line_product.description,
                    'product_barcode': line_product.barcode,
                    # 'product_code': line_product.barcode,
                    'product_currency_id': product_template.currency_id.symbol,
                    'product_uom_id': line_product.uom_id.name,
                    'product_price': float_round(line_product.sale_price, precision_digits=2),  # Format to 2 decimal places
                    'product_pricelists': [],
                }
            else:
                return {'error': 'Product not found for the given barcode.'}

        pricelists_data = []
        product_pricelists = product_template.fixed_pricelist_item_ids.mapped('pricelist_id')

        if product_pricelists:
            for pricelist in product_pricelists:
                items = []
                pricelist_items = product_template.fixed_pricelist_item_ids.filtered(
                    lambda item: item.pricelist_id == pricelist and 
                                 (not item.date_end or item.date_end.date() > today) and
                                 (not item.uom_id or item.uom_id.id == uom_id)
                )

                for pl_item in pricelist_items:
                    if pl_item.compute_price == 'fixed':
                        price = pl_item.fixed_price
                    else:
                        price = product_template.list_price - (product_template.list_price * (pl_item.percent_price / 100.0))

                    price = float_round(price, precision_digits=2)
                    items.append({
                        'pricelist_name': pricelist.name,
                        'price': price,
                        'date_end': pl_item.date_end.strftime('%Y-%m-%d') if pl_item.date_end else None,
                    })

                if items:
                    print(f"Final Items Added for Pricelist {pricelist.name}: {items}")
                    pricelists_data.append({
                        'pricelist_id': pricelist.id,
                        'pricelist_name': pricelist.name,
                        'items': items,
                    })

            vals['product_pricelists'] = pricelists_data

        if not product_pricelists:
            barcode_record = self.env['product.barcode.uom'].search([
                ('barcode', '=', barcode)
            ], limit=1)
            product_template = barcode_record.product_id
            matched_rules = product_template.fixed_pricelist_item_ids.filtered(
                lambda rule: rule.x_scanned_barcode == barcode and
                             (not rule.date_end or rule.date_end.date() >= today) and
                             (not rule.uom_id or rule.uom_id.id == uom_id)
            )

            for rule in matched_rules:

                if rule.compute_price == 'fixed':
                    price = rule.fixed_price
                else:
                    price = product_template.list_price - (
                        product_template.list_price * (rule.percent_price / 100.0)
                    )

                price = float_round(price, 2)

                item_data = {
                    'pricelist_name': rule.pricelist_id.name,
                    'price': price,
                    'date_end': rule.date_end.strftime('%Y-%m-%d') if rule.date_end else None,
                }

                pricelists_data.append({
                    'pricelist_id': rule.pricelist_id.id,
                    'pricelist_name': rule.pricelist_id.name,
                    'items': [item_data],  # << SAME FORMAT AS NORMAL FLOW
                })

            vals['product_pricelists'] = pricelists_data
        return vals
