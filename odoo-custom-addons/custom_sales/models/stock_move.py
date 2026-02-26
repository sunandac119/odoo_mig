from odoo import models, fields, api

class StockMove(models.Model):
    _inherit = 'stock.move'

    def _get_price_unit(self):
        """ Returns the unit price for the move """
        self.ensure_one()

        if self.sale_line_id and self.product_id.id == self.sale_line_id.product_id.id:
            # This is a sale_stock move, update price_unit with sale_order_line cost
            self.price_unit = self.sale_line_id.cost

        return super(StockMove, self)._get_price_unit()
