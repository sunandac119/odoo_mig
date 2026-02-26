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
            # 'account_partial_reconcile': [],
            # 'account_payment': [],
            # 'account_move': [],
            # 'account_move_line': [],
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

        # ====== COMMENT OUT INVOICE/ACTION MOVE/RECONCILE/PAYMENT LOGIC ======

        # invoices = self.env['account.move'].search([('invoice_origin', 'in', order_names)])
        # all_ids['account_move'] += invoices.ids
        # all_ids['account_move_line'] += invoices.mapped('line_ids').ids

        # reconciles = self.env['account.partial.reconcile'].search([
        #     '|',
        #     ('debit_move_id.move_id', 'in', invoices.ids),
        #     ('credit_move_id.move_id', 'in', invoices.ids)
        # ])
        # all_ids['account_partial_reconcile'] += reconciles.ids

        # cr.execute("""
        #     SELECT DISTINCT ap.id
        #     FROM account_payment ap
        #     JOIN account_move am ON am.id = ap.move_id
        #     WHERE am.invoice_origin IN %s
        # """, (order_names,))
        # payment_ids = [r[0] for r in cr.fetchall()]
        # all_ids['account_payment'] += payment_ids
        # =====================================================================


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

                # sql_first_tables = ['account_partial_reconcile', 'account_payment', 'account_move']

                # if table in sql_first_tables:
                #     for table in sql_first_tables:
                #         if table in all_ids:
                #             id_tuple = tuple(all_ids[table])
                #             if not id_tuple:
                #                 _logger.info(f"Skipping {table} — no records to delete")
                #                 continue
                #             _logger.info(f"Deleting from {table} using SQL (priority model)")
                #             cr.execute(f"DELETE FROM {table} WHERE id IN %s", (id_tuple,))
                #             cr.commit()

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
            # 'account_partial_reconcile': [],
            # 'account_payment': [],
            # 'account_move': [],
            # 'account_move_line': [],
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

        # ====== COMMENT OUT INVOICE/ACTION MOVE/RECONCILE/PAYMENT LOGIC ======
        
        # invoices = self.env['account.move'].search([('invoice_origin', 'in', order_names)])
        # all_ids['account_move'] += invoices.ids
        # all_ids['account_move_line'] += invoices.mapped('line_ids').ids
        
        # reconciles = self.env['account.partial.reconcile'].search([
        #     '|',
        #     ('debit_move_id.move_id', 'in', invoices.ids),
        #     ('credit_move_id.move_id', 'in', invoices.ids)
        # ])
        # all_ids['account_partial_reconcile'] += reconciles.ids
        
        # cr.execute("""
        #     SELECT DISTINCT ap.id
        #     FROM account_payment ap
        #     JOIN account_move am ON am.id = ap.move_id
        #     WHERE am.invoice_origin IN %s
        # """, (order_names,))
        # payment_ids = [r[0] for r in cr.fetchall()]
        # all_ids['account_payment'] += payment_ids
        # =====================================================================

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

                # sql_first_tables = [
                #     'account_partial_reconcile',
                #     'account_payment',
                #     'account_move',
                # ]

                # if table in sql_first_tables:
                #     for table in sql_first_tables:
                #         if table in all_ids:
                #             id_tuple = tuple(all_ids[table])
                #             if not id_tuple:
                #                 continue
                #             _logger.info(f"Deleting from {table} using SQL (priority model)")
                #             cr.execute(f"DELETE FROM {table} WHERE id IN %s", (id_tuple,))
                #             cr.commit()

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
    def _cron_delete_old_mrp_order(self):
        _logger.info("Manufacture Order Batch Deletion.")
        """Force-delete manufacturing orders and all related records older than 13 months."""
        cutoff_date = datetime.today() - relativedelta(months=13)
        cutoff_str = fields.Datetime.to_string(cutoff_date)
        BATCH_SIZE = 50
        cr = self.env.cr

        old_mrp = self.env['mrp.production'].search(
            [('create_date', '<', cutoff_str)],
            limit=BATCH_SIZE
        )
        if not old_mrp:
            return

        mrp_names = tuple(old_mrp.mapped('name')) or ('',)
        mrp_ids = tuple(old_mrp.ids) or (0,)

        cr.execute("""
            SELECT id FROM stock_picking WHERE origin IN %s
        """, (mrp_names,))
        picking_ids = [r[0] for r in cr.fetchall()] or []

        if picking_ids:
            cr.execute("""
                SELECT id FROM stock_move WHERE picking_id IN %s
            """, (tuple(picking_ids),))
            stock_move_ids = [r[0] for r in cr.fetchall()] or []

            if stock_move_ids:
                cr.execute("""
                    DELETE FROM stock_valuation_layer
                    WHERE stock_move_id IN %s
                """, (tuple(stock_move_ids),))
                cr.commit()

                cr.execute("""
                    DELETE FROM stock_move_line WHERE move_id IN %s
                """, (tuple(stock_move_ids),))
                cr.commit()

                cr.execute("""
                    DELETE FROM stock_move WHERE id IN %s
                """, (tuple(stock_move_ids),))
                cr.commit()

            cr.execute("""
                DELETE FROM stock_picking WHERE id IN %s
            """, (tuple(picking_ids),))
            cr.commit()
            
        else:
            cr.execute("""
                SELECT id FROM stock_move WHERE origin IN %s
            """, (tuple(mrp_names),))
            stock_move_ids = [r[0] for r in cr.fetchall()] or []

            if stock_move_ids:
                cr.execute("""
                    DELETE FROM stock_valuation_layer
                    WHERE stock_move_id IN %s
                """, (tuple(stock_move_ids),))
                cr.commit()

                cr.execute("""
                    DELETE FROM stock_move_line WHERE move_id IN %s
                """, (tuple(stock_move_ids),))
                cr.commit()

                cr.execute("""
                    DELETE FROM stock_move WHERE id IN %s
                """, (tuple(stock_move_ids),))
                cr.commit()

        bom_ids = old_mrp.mapped('bom_id').ids or []
        if bom_ids:
            cr.execute("""
                DELETE FROM mrp_bom_line WHERE bom_id IN %s
            """, (tuple(bom_ids),))
            cr.commit()

            cr.execute("""
                DELETE FROM mrp_bom WHERE id IN %s
            """, (tuple(bom_ids),))
            cr.commit()

        cr.execute("""
            DELETE FROM mrp_production WHERE id IN %s
        """, (mrp_ids,))
        cr.commit()
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

        # invoices = self.env['account.move'].search([('invoice_origin', 'in', order_names)])
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
        # all_ids['account_move_line'] += old_invoice.mapped('line_ids').ids