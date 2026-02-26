from odoo import api, models

class BarcodeLookup(models.AbstractModel):
    _name = 'multi.uom.barcode.lookup.mixin'

    @api.model
    def lookup_by_multi_uom_barcode(self, barcode, partner_id=None, pricelist_id=None, qty=1.0):
        # Search by barcode from f.pos.multi.uom.barcode.lines
        line = self.env['f.pos.multi.uom.barcode.lines'].search([('barcode', '=', barcode)], limit=1)
        if not line:
            return {}

        # Find product.product from product.template
        product = self.env['product.product'].search([('product_tmpl_id', '=', line.uom_barcode.id)], limit=1)
        if not product:
            return {}

        uom = line.uom
        fallback_price = line.sale_price

        # Compute price via bi_multi_uom_pricelist logic if available
        final_price = fallback_price
        if pricelist_id:
            pricelist = self.env['product.pricelist'].browse(pricelist_id)
            partner = self.env['res.partner'].browse(partner_id) if partner_id else None
            context = dict(self._context or {})
            context.update({'uom': uom.id})
            price_data = pricelist.with_context(context)._compute_price_rule([(product, qty, partner)])
            final_price = price_data.get(product.id, (fallback_price, None))[0] or fallback_price

        return {
            'product': product,
            'product_id': product.id,
            'product_template_id': line.uom_barcode.id,
            'uom_id': uom.id,
            'uom_name': uom.name,
            'price': final_price,
            'sale_price': fallback_price
        }
