from odoo import models, fields, api
import logging

_logger = logging.getLogger(__name__)


class StockPicking(models.Model):
	_inherit = 'stock.picking'

	# @api.model
	# def action_delete_picking(self):
	# 	self.env.cr.execute("""
    #         DELETE FROM stock_picking
    #         WHERE id IN (
    #             SELECT id FROM stock_picking
    #             LIMIT 1000000
    #         )
    #     """)


class StockMoveLine(models.Model):
    _inherit = 'stock.move.line'

    @api.model
    def action_delete_stock_moves(self):
        _logger.info("\n\n Starting deletion of stock_move records.")
        self.env.cr.execute("""
            DELETE FROM stock_move
            WHERE id IN (
                SELECT id FROM stock_move
                LIMIT 1000000
            )
        """)
        _logger.info("\n\n Deleted up to 1,000,000 records from stock_move.")

        _logger.info("\n\n Starting deletion of stock_move_line records.")
        self.env.cr.execute("""
            DELETE FROM stock_move_line
            WHERE id IN (
                SELECT id FROM stock_move_line
                LIMIT 1000000
            )
        """)
        _logger.info("\n\n Deleted up to 1,000,000 records from stock_move_line.")