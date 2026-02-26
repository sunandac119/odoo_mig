from odoo import models, api


class PurchaseOrder(models.Model):
    _inherit = 'purchase.order'

    def button_confirm(self):
        return super(
            PurchaseOrder,
            self.with_context(skip_barcode_validation=True)
        ).button_confirm()


class PurchaseOrderLine(models.Model):
    _inherit = 'purchase.order.line'

    @api.onchange('x_scanned_barcode')
    def _onchange_product_barcode_set_price(self):
        for line in self:
            if not line.x_scanned_barcode:
                continue

            barcode_rec = self.env['product.barcode.uom'].search(
                [('barcode', '=', line.x_scanned_barcode)],
                limit=1
            )

            if not barcode_rec or not barcode_rec.product_id:
                continue

            # barcode_rec.product_id is product.template
            template = barcode_rec.product_id

            # Get first variant
            variant = template.product_variant_id

            # Set variant to purchase line
            line.product_id = variant

            # Set UoM
            line.product_uom = barcode_rec.uom_id or variant.uom_po_id

            # Factor
            factor_inv = line.product_uom.factor_inv or 1.0

            # Sales price from template
            list_price = template.list_price or 0.0

            line.price_unit = list_price * factor_inv
            print('aaaaaaaaaaaaaaaaaaaaaa', line.price_unit)

class StockMove(models.Model):
    _inherit = 'stock.move'

    @api.model
    def create(self, vals):
        if self.env.context.get('skip_barcode_validation'):
            return super().create(vals)

        picking_id = vals.get('picking_id')
        product_id = vals.get('product_id')

        if picking_id and product_id:
            picking = self.env['stock.picking'].browse(picking_id)

            allowed_product_ids = picking.move_ids_without_package.mapped('product_id').ids

            if allowed_product_ids and product_id not in allowed_product_ids:
                return self.browse()

        record = super().create(vals)
        return record


class StockMove(models.Model):
    _inherit = 'stock.move'

    @api.depends(
        'move_line_ids.qty_done',
        'move_line_ids.product_uom_id',
        'move_line_nosuggest_ids.qty_done',
        'picking_type_id'
    )
    def _quantity_done_compute(self):
        if self.env.context.get('skip_barcode_validation'):
            return super().create(vals)
        else:
            super()._quantity_done_compute()
            for move in self:
                if move.quantity_done > move.product_uom_qty:
                    move.quantity_done = move.product_uom_qty
