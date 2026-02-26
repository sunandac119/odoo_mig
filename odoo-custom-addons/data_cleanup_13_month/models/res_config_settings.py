from datetime import datetime, timedelta, time
from dateutil.relativedelta import relativedelta
from odoo import api, fields, models, _
from odoo.exceptions import UserError
import pytz
import xmlrpc.client as xmlrpclib
import logging
from urllib.parse import urlparse

_logger = logging.getLogger(__name__)


class ResConfigSettings(models.TransientModel):
    _inherit = 'res.config.settings'

    @api.model
    def _cron_delete_old_sales_order(self, batch_size=200):
        """Delete old sale orders and all linked records using batched SQL deletions."""
        cutoff_date = datetime.today() - relativedelta(months=13)
        old_orders = self.env['sale.order'].search([('create_date', '<', cutoff_date)], limit=batch_size)

        if not old_orders:
            _logger.info("No Sale Orders found older than 13 months.")
            return True

        cr = self.env.cr

        all_ids = {
            'sale_order_line': [],
            'stock_picking': [],
            'stock_valuation_layer': [],
            'stock_move_line': [],
            'stock_move': [],
            'sale_order': [],
        }

        order_names = tuple(old_orders.mapped('name'))
        pickings = self.env['stock.picking'].search([('origin', 'in', order_names)])
        moves = self.env['stock.move'].search([('picking_id', 'in', pickings.ids)])
        move_lines = self.env['stock.move.line'].search([('move_id', 'in', moves.ids)])
        valuation_layers = self.env['stock.valuation.layer'].search([('stock_move_id', 'in', moves.ids)])

        all_ids['stock_valuation_layer'] += valuation_layers.ids
        all_ids['stock_move_line'] += move_lines.ids
        all_ids['stock_move'] += moves.ids
        all_ids['stock_picking'] += pickings.ids

        all_ids['sale_order_line'] += old_orders.mapped('order_line').ids
        all_ids['sale_order'] += old_orders.ids

        # === Now delete model by model (batch SQL) ===
        for model, ids in all_ids.items():
            if not ids:
                continue
            try:
                table = model.replace('.', '_')
                id_tuple = tuple(ids)
                _logger.info(f"Deleting {len(ids)} records from {table} (IDs: {id_tuple[:10]}...)")

                # Define ORM-sensitive models
                orm_models = {
                    # 'account_move_line': 'account.move.line',
                }

                if table in orm_models:
                    orm_model = orm_models[table]
                    recs = self.env[orm_model].browse(ids)
                    _logger.info(f"Using ORM unlink for {len(recs)} {orm_model} records")
                    recs.unlink()

                else:
                    _logger.info(f"Deleting from {table} using SQL")
                    cr.execute(f"DELETE FROM {table} WHERE id IN %s", (id_tuple,))
                    cr.commit()

            except Exception as e:
                _logger.warning(f"Failed to delete from {model}: {e}")
                cr.rollback()

        _logger.info("Batch Deletion Summary:")
        for model, ids in all_ids.items():
            _logger.info(f"  - {model}: {len(ids)} deleted")

        return True


    @api.model
    def _cron_delete_old_purchase_order(self, batch_size=200):
        cutoff_date = datetime.today() - relativedelta(months=13)
        old_orders = self.env['purchase.order'].search([('create_date', '<', cutoff_date)], limit=batch_size)

        if not old_orders:
            _logger.info("No Purchase Orders found older than 13 months.")
            return True

        cr = self.env.cr

        # Collect all related record IDs
        all_ids = {
            'purchase_order_line': [],
            'stock_picking': [],
            'stock_valuation_layer': [],
            'stock_move_line': [],
            'stock_move': [],
            'purchase_order': [],
        }

        order_names = tuple(old_orders.mapped('name'))
        pickings = self.env['stock.picking'].search([('origin', 'in', order_names)])
        moves = self.env['stock.move'].search([('picking_id', 'in', pickings.ids)])
        move_lines = self.env['stock.move.line'].search([('move_id', 'in', moves.ids)])
        valuation_layers = self.env['stock.valuation.layer'].search([('stock_move_id', 'in', moves.ids)])

        all_ids['stock_valuation_layer'] += valuation_layers.ids
        all_ids['stock_move_line'] += move_lines.ids
        all_ids['stock_move'] += moves.ids
        all_ids['stock_picking'] += pickings.ids

        all_ids['purchase_order_line'] += old_orders.mapped('order_line').ids
        all_ids['purchase_order'] += old_orders.ids

        for model, ids in all_ids.items():
            if not ids:
                continue

            try:
                table = model.replace('.', '_')
                id_tuple = tuple(ids)

                _logger.info(f"Deleting {len(ids)} records from {table} (IDs: {id_tuple[:10]}...)")

                orm_models = {
                    # 'account_move_line': 'account.move.line',
                }


                if table in orm_models:
                    orm_model = orm_models[table]
                    recs = self.env[orm_model].browse(ids)
                    _logger.info(f"Using ORM unlink for {len(recs)} {orm_model} records")
                    recs.unlink()

                else:
                    _logger.info(f"Deleting from {table} using SQL")
                    cr.execute(f"DELETE FROM {table} WHERE id IN %s", (id_tuple,))
                    cr.commit()

            except Exception as e:
                _logger.warning(f"Failed to delete from {model}: {e}")
                cr.rollback()

        _logger.info("Purchase Order Batch Deletion Summary:")
        for model, ids in all_ids.items():
            _logger.info(f"  - {model}: {len(ids)} deleted")

        return True

    @api.model
    def _cron_delete_old_mrp_order(self, batch_size=200):
        """Delete old MRP orders and linked records using batched SQL deletions."""
        _logger.info("MRP Deletion Cron Started")

        cutoff_date = datetime.today() - relativedelta(months=13)
        old_mrp = self.env['mrp.production'].search(
            [('create_date', '<', cutoff_date)],
            limit=batch_size
        )

        if not old_mrp:
            _logger.info("No MRP Production records older than 13 months.")
            return True

        cr = self.env.cr

        all_ids = {
            'mrp_production': [],
            'stock_move': [],
            'stock_move_line': [],
            'stock_valuation_layer': [],
            'stock_picking': [],
            'mrp_bom': [],
            'mrp_bom_line': [],
        }

        all_ids['mrp_production'] += old_mrp.ids

        boms = old_mrp.mapped('bom_id')
        all_ids['mrp_bom'] += boms.ids

        bom_lines = self.env['mrp.bom.line'].search([('bom_id', 'in', boms.ids)])
        all_ids['mrp_bom_line'] += bom_lines.ids

        pickings = self.env['stock.picking'].search([
            ('origin', 'in', old_mrp.mapped('name'))
        ])
        all_ids['stock_picking'] += pickings.ids

        stock_moves = self.env['stock.move'].search([
            '|',
            ('picking_id', 'in', pickings.ids),
            ('origin', 'in', old_mrp.mapped('name')),
        ])
        all_ids['stock_move'] += stock_moves.ids

        # STOCK MOVE LINES
        move_lines = self.env['stock.move.line'].search([
            ('move_id', 'in', stock_moves.ids)
        ])
        all_ids['stock_move_line'] += move_lines.ids

        # STOCK VALUATION LAYERS
        svl = self.env['stock.valuation.layer'].search([
            ('stock_move_id', 'in', stock_moves.ids)
        ])
        all_ids['stock_valuation_layer'] += svl.ids


        sql_priority = [
            'stock_move_line',
            'stock_move',
            'mrp_production',
        ]

        for model in sql_priority:
            ids = all_ids.get(model)
            if not ids:
                continue

            try:
                table = model
                id_tuple = tuple(ids)

                _logger.info(f"Deleting from {table} using SQL ({len(ids)} records)")
                cr.execute(f"DELETE FROM {table} WHERE id IN %s", (id_tuple,))
                cr.commit()

            except Exception as e:
                _logger.warning(f"SQL delete failed for {model}: {e}")
                cr.rollback()

        orm_models = {
            'stock_picking': 'stock.picking',
            'mrp_bom': 'mrp.bom',
            'mrp_bom_line': 'mrp.bom.line',
            'stock_valuation_layer': 'stock.valuation.layer',
        }

        for model, odoo_model in orm_models.items():
            ids = all_ids.get(model)
            if not ids:
                continue

            try:
                recs = self.env[odoo_model].browse(ids)
                if recs.exists():
                    _logger.info(f"Deleting {len(recs)} from {model} via ORM unlink")
                    recs.unlink()
            except Exception as e:
                _logger.warning(f"ORM delete failed for {model}: {e}")

        _logger.info("MRP Deletion Summary:")
        for model, ids in all_ids.items():
            _logger.info(f" - {model}: {len(ids)} deleted")
    
        _logger.info("Manufacture Order Batch Deletion Successfully")
        #Unlink Expired Price Rule and Pricelist
        self.cron_delete_expired_price_rule()
        _logger.info("Expired Pricelist Batch Deletion Successfully")

    @api.model
    def cron_delete_expired_price_rule(self):
        today = fields.Datetime.now()
        cr = self.env.cr

        cr.execute("""
            DELETE FROM product_pricelist_item
            WHERE date_end IS NOT NULL AND date_end < %s
        """, (today,))
        cr.commit()

        cr.execute("""
            DELETE FROM product_supplierinfo
            WHERE date_end IS NOT NULL AND date_end < %s
        """, (today,))
        cr.commit()

    @api.model
    def _cron_delete_old_invoices(self, batch_size=100):
        """Delete old sale orders and all linked records using batched SQL deletions."""
        cutoff_date = datetime.today() - relativedelta(months=13)
        old_invoice = self.env['account.move'].search([('create_date', '<', cutoff_date)], limit=batch_size)

        if not old_invoice:
            _logger.info("No Account Move found older than 13 months.")
            return True

        cr = self.env.cr

        all_ids = {
            'account_partial_reconcile': [],
            'account_payment': [],
            'account_move': [],
            'account_move_line': [],
            }

        all_ids['account_move'] += old_invoice.ids
        all_ids['account_move_line'] += old_invoice.mapped('line_ids').ids
        
        reconciles = self.env['account.partial.reconcile'].search([
            '|',
            ('debit_move_id.move_id', 'in', old_invoice.ids),
            ('credit_move_id.move_id', 'in', old_invoice.ids)
        ])
        all_ids['account_partial_reconcile'] += reconciles.ids
        
        invoice_origins = tuple({origin for origin in old_invoice.mapped('invoice_origin') if origin}) 
        if not invoice_origins:
            invoice_origins = ('',) 

        cr.execute("""
            SELECT DISTINCT ap.id
            FROM account_payment ap
            JOIN account_move am ON am.id = ap.move_id
            WHERE am.invoice_origin IN %s
        """, (invoice_origins,))
        payment_ids = [r[0] for r in cr.fetchall()]
        all_ids['account_payment'] += payment_ids

        for model, ids in all_ids.items():
            if not ids:
                continue

            try:
                table = model.replace('.', '_')
                id_tuple = tuple(ids)

                _logger.info(f"Deleting {len(ids)} records from {table} (IDs: {id_tuple[:10]}...)")

                orm_models = {
                    'account_move_line': 'account.move.line',
                }

                sql_first_tables = [
                    'account_partial_reconcile',
                    'account_payment',
                    'account_move',
                ]

                if table in sql_first_tables:
                    for table in sql_first_tables:
                        if table in all_ids:
                            id_tuple = tuple(all_ids[table])
                            if not id_tuple:
                                continue
                            _logger.info(f"Deleting from {table} using SQL (priority model)")
                            cr.execute(f"DELETE FROM {table} WHERE id IN %s", (id_tuple,))
                            cr.commit()

            except Exception as e:
                _logger.warning(f"Failed to delete from {model}: {e}")
                cr.rollback()

        _logger.info("Purchase Order Batch Deletion Summary:")
        for model, ids in all_ids.items():
            _logger.info(f"  - {model}: {len(ids)} deleted")

        return True
