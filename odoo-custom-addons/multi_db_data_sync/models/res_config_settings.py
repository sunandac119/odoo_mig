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

    url = fields.Char(string="URL", config_parameter="multi_db_data_sync.url")
    db_name = fields.Char(string="Database Name", config_parameter="multi_db_data_sync.db_name")
    username = fields.Char(string="Username", config_parameter="multi_db_data_sync.username")
    password = fields.Char(string="Password", config_parameter="multi_db_data_sync.password")

    @api.model
    def _cron_sync_data(self):
        """Cron to sync today's sale orders to external Odoo DB."""
        _logger.info("\n\n >>> Running sale order sync cron...")

        ICP = self.env['ir.config_parameter'].sudo()
        url = ICP.get_param("multi_db_data_sync.url")
        db = ICP.get_param("multi_db_data_sync.db_name")
        username = ICP.get_param("multi_db_data_sync.username")
        password = ICP.get_param("multi_db_data_sync.password")

        _logger.info("\n\n >>> Sync Config: url=%s, db=%s, username=%s", url, db, username)

        if not url or not db or not username or not password:
            raise UserError("Missing external DB credentials in settings.")

        parsed_url = urlparse(url)
        if parsed_url.scheme not in ("http", "https") or not parsed_url.netloc:
            raise UserError("Invalid URL format.")

        try:
            # External connection
            common = xmlrpclib.ServerProxy(f"{url}/xmlrpc/2/common", allow_none=True)
            uid = common.authenticate(db, username, password, {})
            if not uid:
                raise UserError("External DB authentication failed.")
            models = xmlrpclib.ServerProxy(f"{url}/xmlrpc/2/object", allow_none=True)

            # Get timezone-aware dates
            user_tz = pytz.timezone(self.env.user.tz or 'UTC')
            now_user_tz = datetime.now(user_tz)
            start_dt_user = datetime.combine(now_user_tz.date(), time.min)
            end_dt_user = datetime.combine(now_user_tz.date(), time.max)

            start_dt_utc = start_dt_user.astimezone(pytz.UTC)
            end_dt_utc = end_dt_user.astimezone(pytz.UTC)

            _logger.info("\n\n Sync Config: url=%s, db=%s, username=%s", url, db, username)
            _logger.info("\n\n User timezone: %s, Start=%s, End=%s", now_user_tz, start_dt_utc, end_dt_utc)

            # Pass required params to the next method
            self._cron_sync_sale_order_data(models, db, uid, password, start_dt_utc, end_dt_utc)
            self._cron_sync_purchase_order_data(models, db, uid, password, start_dt_utc, end_dt_utc)
            self._cron_sync_pickings(models, db, uid, password, start_dt_utc, end_dt_utc)
            self._cron_sync_customers(models, db, uid, password, start_dt_utc, end_dt_utc)
            self._cron_sync_manufacturing_orders(models, db, uid, password, start_dt_utc, end_dt_utc)
            self._cron_sync_bom_data(models, db, uid, password, start_dt_utc, end_dt_utc)
            # ====================== _cron_sync_account_move =========== Dev X3
            self._cron_sync_account_move(models, db, uid, password, start_dt_utc, end_dt_utc)
            # ====================== _cron_sync_payments =========== Dev X3
            self._cron_sync_payments(models, db, uid, password, start_dt_utc, end_dt_utc)
            # ====================== _cron_sync_journal_entry =========== Dev X3
            self._cron_sync_journal_entry(models, db, uid, password, start_dt_utc, end_dt_utc)
            # ================= pos order ============= Dev X1
            self._cron_sync_pos_order_data(models, db, uid, password, start_dt_utc, end_dt_utc)
            # ================= pos order config ============= Dev X2
            self._cron_sync_pos_config_data(models, db, uid, password, start_dt_utc, end_dt_utc)
            _logger.info("SYNC Successfully")


        except Exception as e:
            _logger.error("Error in sale order sync: %s", str(e))
            raise

    @api.model
    def _cron_sync_sale_order_data(self, models, db, uid, password, start_dt_utc, end_dt_utc):
        sale_orders = self.env['sale.order'].search([
            ('date_order', '>=', start_dt_utc.strftime("%Y-%m-%d %H:%M:%S")),
            ('date_order', '<=', end_dt_utc.strftime("%Y-%m-%d %H:%M:%S")),
        ])
        _logger.info("Found %s sale orders to sync", len(sale_orders))

        for order in sale_orders:
            try:
                _logger.info("Syncing Sale Order: %s", order.name)

                # --- Check if order exists ---
                existing = models.execute_kw(
                    db, uid, password,
                    'sale.order', 'search',
                    [[('name', '=', order.name)]],
                    {'limit': 1}
                )

                if existing:
                    order_ext_id = existing[0]
                    _logger.info("Order %s already exists, syncing children...", order.name)
                    partner_ext_id = self._map_record(models, db, uid, password, 'res.partner', order.partner_id, 'name')
                else:
                    # --- Sync Partner ---
                    partner_ext_id = self._map_record(
                        models, db, uid, password, 'res.partner', order.partner_id, 'name',
                        extra_vals={
                            'street': order.partner_id.street,
                            'city': order.partner_id.city,
                            'phone': order.partner_id.phone,
                            'email': order.partner_id.email,
                        }
                    )

                    # --- Create Sale Order Header ---
                    order_vals = {
                        'name': order.name,
                        'validate_picking': True,
                        'partner_id': partner_ext_id,
                        'team_id': self._map_record(models, db, uid, password, 'crm.team', order.team_id, 'name'),
                        'client_order_ref': order.client_order_ref,
                        'date_order': str(order.date_order),
                        'amount_total': order.amount_total,
                        'state': order.state,
                        'so_invoice_count': len(order.invoice_ids),
                        'signed_by': order.signed_by,
                        'signed_on': order.signed_on,
                        'user_id': self._map_record(models, db, uid, password, 'res.users', order.user_id, 'login'),
                        'payment_term_id': self._map_record(models, db, uid, password, 'account.payment.term', order.payment_term_id, 'name'),
                    }
                    order_ext_id = models.execute_kw(db, uid, password, 'sale.order', 'create', [order_vals])
                    _logger.info("Created new sale order %s", order.name)

                # --- Sync Sale Order Lines ---
                for line in order.order_line:
                    product_ext_id = self._map_product(models, db, uid, password, line.product_id)
                    uom_ext_id = self._map_uom(models, db, uid, password, line.product_uom)
                    barcode_val = line.x_scanned_barcode or (line.product_id.barcode if line.product_id else False)

                    # Avoid duplicates
                    existing_line = models.execute_kw(
                        db, uid, password,
                        'sale.order.line', 'search',
                        [[('order_id', '=', order_ext_id),
                          ('product_id', '=', product_ext_id),
                          ('product_uom', '=', uom_ext_id),
                          ('x_scanned_barcode', '=', barcode_val)]],
                        {'limit': 1}
                    )
                    if existing_line:
                        continue

                    line_vals = {
                        'order_id': order_ext_id,
                        'product_id': product_ext_id,
                        'name': line.name,
                        'x_scanned_barcode': barcode_val,
                        'product_uom': uom_ext_id,
                        'product_uom_qty': float(line.product_uom_qty or 0.0),
                        'price_unit': float(line.price_unit or 0.0),
                        'tax_id': [(6, 0, [
                            self._map_record(models, db, uid, password, 'account.tax', tax, 'name')
                            for tax in line.tax_id
                        ])] if line.tax_id else [],
                    }
                    models.execute_kw(db, uid, password, 'sale.order.line', 'create', [line_vals])

                _logger.info("Synced lines for %s", order.name)

                # --- Sync Pickings ---
                # for picking in order.picking_ids:
                #     picking_ext_id = self._map_picking(
                #         models, db, uid, password,
                #         picking, partner_ext_id,
                #         origin=order.name,
                #         order_ext_id=order_ext_id
                #     )

                #     # --- Sync Stock Moves ---
                #     for move in picking.move_ids_without_package:
                #         product_ext = self._map_product(models, db, uid, password, move.product_id)
                #         uom_ext = self._map_record(models, db, uid, password, 'uom.uom', move.product_uom, 'name')

                #         move_vals = {
                #             'name': move.name,
                #             'description_picking': move.description_picking,
                #             'x_scanned_barcode': move.x_scanned_barcode,
                #             'picking_id': picking_ext_id,
                #             'product_id': product_ext,
                #             'product_uom_qty': move.product_uom_qty,
                #             'product_uom': uom_ext,
                #             'state': move.state,
                #             'location_id': self._map_record(models, db, uid, password, 'stock.location', move.location_id, 'name'),
                #             'location_dest_id': self._map_record(models, db, uid, password, 'stock.location', move.location_dest_id, 'name'),
                #         }

                #         # Create move with flag (to apply UOM/Barcode logic)
                #         models.execute_kw(
                #             db, uid, password,
                #             'stock.move', 'create',
                #             [move_vals],
                #             {'context': {'apply_barcode_uom_logic': True}}
                #         )

                #     # --- Sync Move Lines (qty_done lives here)
                #     for mline in picking.move_line_ids_without_package:
                #         product_ext = self._map_product(models, db, uid, password, mline.product_id)
                #         uom_ext = self._map_record(models, db, uid, password, 'uom.uom', mline.product_uom_id, 'name')

                #         mline_vals = {
                #             'description': mline.description,
                #             'x_scanned_barcode': mline.x_scanned_barcode,
                #             'picking_id': picking_ext_id,
                #             'product_id': product_ext,
                #             'qty_done': mline.qty_done,  # correct place
                #             'product_uom_id': uom_ext,
                #             'location_id': self._map_record(models, db, uid, password, 'stock.location', mline.location_id, 'name'),
                #             'location_dest_id': self._map_record(models, db, uid, password, 'stock.location', mline.location_dest_id, 'name'),
                #         }

                #         models.execute_kw(db, uid, password, 'stock.move.line', 'create', [mline_vals])



                # --- Sync Invoices ---
                for invoice in order.invoice_ids:
                    try:
                        # Map partner & journal first
                        journal_ext_id = self._map_record(models, db, uid, password, 'account.journal', invoice.journal_id, 'name')

                        invoice_vals = {
                            'name': invoice.name,
                            'move_type': invoice.move_type or 'out_invoice',
                            'invoice_origin': order.name,
                            'invoice_date': str(invoice.invoice_date) if invoice.invoice_date else False,
                            'invoice_date_due': str(invoice.invoice_date_due) if invoice.invoice_date_due else False,
                            'partner_id': partner_ext_id,
                            'amount_total': invoice.amount_total,
                            'state': 'posted' if invoice.state == 'posted' else 'draft',
                            'payment_state': invoice.payment_state,
                            'journal_id': journal_ext_id,
                        }

                        # Create or update invoice
                        invoice_ext_id = self._map_record(models, db, uid, password, 'account.move', invoice, 'name', extra_vals=invoice_vals)

                        # --- Sync Invoice Lines ---
                        for inv_line in invoice.invoice_line_ids:
                            product_ext_id = self._map_product(models, db, uid, password, inv_line.product_id)
                            uom_ext_id = self._map_record(models, db, uid, password, 'uom.uom', inv_line.product_uom_id, 'name')

                            # Link sale order line by product & order
                            ext_sale_line = models.execute_kw(
                                db, uid, password, 'sale.order.line', 'search',
                                [[
                                    ('order_id', '=', order_ext_id),
                                    ('product_id', '=', product_ext_id),
                                ]],
                                {'limit': 1}
                            )

                            inv_line_vals = {
                                'move_id': invoice_ext_id,
                                'product_id': product_ext_id,
                                'name': inv_line.name,
                                'quantity': inv_line.quantity,
                                'price_unit': inv_line.price_unit,
                                'product_uom_id': uom_ext_id,
                                'sale_line_ids': [(6, 0, ext_sale_line)] if ext_sale_line else [],
                            }

                            models.execute_kw(db, uid, password, 'account.move.line', 'create', [inv_line_vals])

                        # Force recompute of invoice_count
                        models.execute_kw(
                            db, uid, password,
                            'sale.order', 'write',
                            [[order_ext_id], {}]
                        )

                    except Exception as e:
                        _logger.error("Failed syncing invoice %s for %s: %s", invoice.name, order.name, e)

                    # --- Sync Payments ---
                    for payment in invoice.payment_id:
                        partner_ext = partner_ext_id
                        journal_ext = self._map_record(models, db, uid, password, 'account.journal', payment.journal_id, 'name')

                        payment_vals = {
                            'name': payment.name,
                            'payment_type': payment.payment_type,
                            'partner_type': payment.partner_type,
                            'partner_id': partner_ext,
                            'amount': payment.amount,
                            'payment_date': str(payment.payment_date),
                            'journal_id': journal_ext,
                            'ref': payment.ref,
                            'communication': payment.communication,
                            'state': payment.state,
                        }

                        payment_ext_id = self._map_record(models, db, uid, password, 'account.payment', payment, 'name', extra_vals=payment_vals)

                        # Link payment to invoice
                        # models.execute_kw(
                        #     db, uid, password, 'account.move', 'write',
                        #     [[invoice_ext_id], {'payment_id': [(4, payment_ext_id)]}]
                        # )

            except Exception as e:
                _logger.error("Failed syncing %s: %s", order.name, str(e))

    @api.model
    def _cron_sync_purchase_order_data(self, models, db, uid, password, start_dt_utc, end_dt_utc):
        """Sync today's purchase orders, bills, and payments to external DB."""
        _logger.info("Starting PO sync from %s to %s", start_dt_utc, end_dt_utc)

        purchase_orders = self.env['purchase.order'].search([
            ('date_order', '>=', start_dt_utc.strftime("%Y-%m-%d %H:%M:%S")),
            ('date_order', '<=', end_dt_utc.strftime("%Y-%m-%d %H:%M:%S")),
        ])
        _logger.info("Found %s purchase orders to sync", len(purchase_orders))

        for po in purchase_orders:
            try:
                # --- Check if PO exists ---
                existing = models.execute_kw(db, uid, password, 'purchase.order', 'search', [[('name', '=', po.name)]], {'limit': 1})
                if existing:
                    _logger.info("PO %s already exists. Skipping.", po.name)
                    continue

                # --- Sync Vendor (Partner) ---
                vendor_ext = self._map_record(
                    models, db, uid, password, 'res.partner', po.partner_id, 'name',
                    extra_vals={
                        'street': po.partner_id.street,
                        'city': po.partner_id.city,
                        'phone': po.partner_id.phone,
                        'email': po.partner_id.email,
                        'supplier_rank': 1,
                    }
                )

                # --- Create Purchase Order Header ---
                po_vals = {
                    'name': po.name,
                    'partner_id': vendor_ext,
                    'origin': po.origin,
                    'date_order': str(po.date_order),
                    'currency_id': self._map_record(models, db, uid, password, 'res.currency', po.currency_id, 'name'),
                    'company_id': self._map_record(models, db, uid, password, 'res.company', po.company_id, 'name'),
                    'user_id': self._map_record(models, db, uid, password, 'res.users', po.user_id, 'login'),
                    'state': po.state,
                    'po_picking_count': len(po.picking_ids),
                    'po_invoice_count': len(po.invoice_ids),
                }
                po_ext_id = models.execute_kw(db, uid, password, 'purchase.order', 'create', [po_vals])
                _logger.info("Synced new purchase order %s", po.name)

                # --- Sync Purchase Order Lines ---
                po_line_map = {}
                for line in po.order_line:
                    product_ext = self._map_product(models, db, uid, password, line.product_id)
                    uom_ext = self._map_record(models, db, uid, password, 'uom.uom', line.product_uom, 'name')

                    line_vals = {
                        'order_id': po_ext_id,
                        'product_id': product_ext,
                        'name': line.name,
                        'date_planned': str(line.date_planned),
                        'product_qty': line.product_qty,
                        'x_scanned_barcode': getattr(line, 'x_scanned_barcode', False),
                        'product_uom': uom_ext,
                        'price_unit': line.price_unit,
                        'taxes_id': [(6, 0, [
                            self._map_record(models, db, uid, password, 'account.tax', tax, 'name')
                            for tax in line.taxes_id
                        ])] if line.taxes_id else [],
                    }
                    line_ext_id = models.execute_kw(db, uid, password, 'purchase.order.line', 'create', [line_vals])
                    po_line_map[line.id] = line_ext_id

                _logger.info("Synced lines for PO %s", po.name)

                # --- Recompute picking count ---
                models.execute_kw(db, uid, password, 'purchase.order', '_compute_picking_count', [[po_ext_id]])

                # --- Sync Pickings and Stock Moves ---
                for picking in po.picking_ids:
                    picking_ext_id = self._map_picking(models, db, uid, password, picking, partner_ext=vendor_ext, origin=po.name, po_ext_id=po_ext_id)
                    picking_ext_id = picking_ext_id[0] if isinstance(picking_ext_id, list) else picking_ext_id

                    # Stock moves
                    for move in picking.move_ids_without_package:
                        product_ext = self._map_product(models, db, uid, password, move.product_id)
                        uom_ext = self._map_record(models, db, uid, password, 'uom.uom', move.product_uom, 'name')
                        move_vals = {
                            'name': move.name,
                            'description_picking': move.description_picking,
                            'x_scanned_barcode': getattr(move, 'x_scanned_barcode', False),
                            'picking_id': picking_ext_id,
                            'product_id': product_ext,
                            'product_uom_qty': move.product_uom_qty,
                            'product_uom': uom_ext,
                            'state': move.state,
                            'location_id': self._map_record(models, db, uid, password, 'stock.location', move.location_id, 'name'),
                            'location_dest_id': self._map_record(models, db, uid, password, 'stock.location', move.location_dest_id, 'name'),
                            'purchase_line_id': po_line_map.get(move.purchase_line_id.id),
                        }
                        move_ext_id = models.execute_kw(db, uid, password, 'stock.move', 'create', [move_vals])

                    # Stock move lines
                    for mline in picking.move_line_ids_without_package:
                        product_ext = self._map_product(models, db, uid, password, mline.product_id)
                        uom_ext = self._map_record(models, db, uid, password, 'uom.uom', mline.product_uom_id, 'name')
                        lot_ext = self._map_lot(models, db, uid, password, mline.lot_id)
                        mline_vals = {
                            'description': mline.description,
                            'x_scanned_barcode': getattr(mline, 'x_scanned_barcode', False),
                            'picking_id': picking_ext_id,
                            'product_id': product_ext,
                            'qty_done': mline.qty_done,
                            'product_uom_id': uom_ext,
                            'lot_id': lot_ext,
                            'location_id': self._map_record(models, db, uid, password, 'stock.location', mline.location_id, 'name'),
                            'location_dest_id': self._map_record(models, db, uid, password, 'stock.location', mline.location_dest_id, 'name'),
                            'move_id': self._map_record(models, db, uid, password, 'stock.move', mline.move_id, 'name'),
                        }
                        models.execute_kw(db, uid, password, 'stock.move.line', 'create', [mline_vals])

                # --- Sync Vendor Bills (Invoices) ---
                for bill in po.invoice_ids:
                    bill_ext = models.execute_kw(db, uid, password, 'account.move', 'search', [[('name','=',bill.name)]], {'limit': 1})
                    if bill_ext:
                        _logger.info("Bill %s already exists. Skipping.", bill.name)
                        continue

                    bill_vals = {
                        'name': bill.name,
                        'move_type': bill.move_type,
                        'partner_id': vendor_ext,
                        'invoice_date': str(bill.invoice_date) if bill.invoice_date else False,
                        'invoice_date_due': str(bill.invoice_date_due) if bill.invoice_date_due else False,
                        'invoice_origin': po.name,
                        'invoice_payment_term_id': self._map_record(models, db, uid, password, bill.invoice_payment_term_id, 'name') if bill.invoice_payment_term_id else False,
                        'invoice_user_id': self._map_record(models, db, uid, password, bill.invoice_user_id, 'login') if bill.invoice_user_id else False,
                    }
                    bill_ext_id = models.execute_kw(db, uid, password, 'account.move', 'create', [bill_vals])

                    if bill.state == 'posted':
                        # Post the bill
                        models.execute_kw(db, uid, password, 'account.move', 'action_post', [[bill_ext_id]])

                    # Sync invoice lines
                    for line in bill.invoice_line_ids:
                        if not line.product_id or line.quantity <= 0:
                            continue
                        product_ext = self._map_product(models, db, uid, password, line.product_id)
                        account_ext = self._map_account(models, db, uid, password, line.account_id)
                        tax_ext_ids = [self._map_record(models, db, uid, password, 'account.tax', tax, 'name') for tax in line.tax_ids]
                        bill_line_vals = {
                            'move_id': bill_ext_id,
                            'product_id': product_ext,
                            'name': line.name,
                            'quantity': line.quantity,
                            'price_unit': line.price_unit,
                            'tax_ids': [(6, 0, tax_ext_ids)] if tax_ext_ids else [],
                            'account_id': account_ext,
                        }
                        models.execute_kw(db, uid, password, 'account.move.line', 'create', [bill_line_vals])

                # --- Sync Payments and link to bills ---
                for bill in po.invoice_ids:
                    for payment in bill.payment_ids:
                        invoice_ext_ids = []
                        if payment.reconciled_invoice_ids:
                            for inv in payment.reconciled_invoice_ids:
                                try:
                                    remote_inv = models.execute_kw(
                                        db, uid, password,
                                        'account.move', 'search_read',
                                        [[('name', '=', inv.name)]],
                                        {'fields': ['id'], 'limit': 1}
                                    )
                                    if remote_inv:
                                        invoice_ext_ids.append(remote_inv[0]['id'])
                                except Exception as e:
                                    _logger.warning("Failed mapping invoice %s for payment %s: %s", inv.name, payment.name, e)

                        payment_vals = {
                            'name': payment.name,
                            'journal_id': journal_ext_id,
                            'partner_type': payment.partner_type,
                            'payment_type': payment.payment_type,
                            'partner_id': partner_ext_id,
                            'destination_account_id': destination_account_ext_id,
                            'partner_bank_id': partner_bank_ext_id,
                            'currency_id': currency_ext_id,
                            'is_internal_transfer': payment.is_internal_transfer,
                            'amount': payment.amount,
                            'date': payment.date or fields.Date.today(),
                            'ref': payment.ref,
                            'payment_method_id': self._map_record(models, db, uid, password, 'account.payment.method', payment.payment_method_id, 'name') if payment.payment_method_id else False,
                            'invoice_ids': [(6, 0, invoice_ext_ids)] if invoice_ext_ids else [],
                        }
                        payment_ext_id = models.execute_kw(db, uid, password, 'account.payment', 'create', [payment_vals])

                        if payment.state == 'posted':
                            models.execute_kw(db, uid, password, 'account.payment', 'action_post', [[payment_ext_id]])
                            _logger.info("Payment %s posted and linked to bill %s", payment.name, bill.name)

            except Exception as e:
                _logger.error("Failed syncing PO %s: %s", po.name, str(e), exc_info=True)

        _logger.info("PO sync completed.")

    @api.model
    def _cron_sync_customers(self, models, db, uid, password, start_dt_utc, end_dt_utc):
        partners = self.env['res.partner'].search([
            # ('customer_rank', '>', 0),
            ('create_date', '>=', start_dt_utc.strftime("%Y-%m-%d %H:%M:%S")),
            ('create_date', '<=', end_dt_utc.strftime("%Y-%m-%d %H:%M:%S")),
        ])
        _logger.info("Found %s new customers to sync", len(partners))

        for partner in partners:
            try:
                existing = models.execute_kw(
                    db, uid, password,
                    'res.partner', 'search',
                    [[('name', '=', partner.name), ('email', '=', partner.email or '')]],
                    {'limit': 1}
                )
                if existing:
                    _logger.info("Customer %s already exists, skipping.", partner.name)
                    continue

                vals = {
                    'name': partner.name,
                    'street': partner.street,
                    'street2': partner.street2,
                    'city': partner.city,
                    'zip': partner.zip,
                    'phone': partner.phone,
                    'mobile': partner.mobile,
                    'email': partner.email,
                    'vat': partner.vat,
                    'company_type': partner.company_type,
                    'country_id': self._map_record(models, db, uid, password, 'res.country', partner.country_id, 'name') if partner.country_id else False,
                    'state_id': self._map_record(models, db, uid, password, 'res.country.state', partner.state_id, 'name') if partner.state_id else False,
                    'customer_rank': partner.customer_rank,
                }
                models.execute_kw(db, uid, password, 'res.partner', 'create', [vals])
                _logger.info("Synced customer %s", partner.name)

            except Exception as e:
                _logger.error("Failed syncing customer %s: %s", partner.name, str(e))

    @api.model
    def _cron_sync_pickings(self, models, db, uid, password, start_dt_utc, end_dt_utc):
        pickings = self.env['stock.picking'].search([
            ('create_date', '>=', start_dt_utc.strftime("%Y-%m-%d %H:%M:%S")),
            ('create_date', '<=', end_dt_utc.strftime("%Y-%m-%d %H:%M:%S")),
        ])
        _logger.info("Found %s new pickings to sync", len(pickings))
        for picking in pickings:
            try:
                existing = models.execute_kw(
                    db, uid, password,
                    'stock.picking', 'search',
                    [[('name', '=', picking.name)]],
                    {'limit': 1}
                )
                if existing:
                    _logger.info("Picking %s already exists, skipping.", picking.name)
                    continue

                # Map partner
                partner_ext = False
                if picking.partner_id:
                    partner_ext = models.execute_kw(
                        db, uid, password,
                        'res.partner', 'search',
                        [[('name', '=', picking.partner_id.name)]],
                        {'limit': 1}
                    )

                # Create picking
                picking_vals = {
                    'name': picking.name,
                    'origin': picking.origin,
                    'partner_id': partner_ext and partner_ext[0] or False,
                    'picking_type_id': picking.picking_type_id.id,
                    'scheduled_date': str(picking.scheduled_date) if picking.scheduled_date else False,
                    'state': picking.state,
                    'purchase_id': False,
                    'sale_id': False,
                    'location_id': self._map_record(models, db, uid, password, 'stock.location', picking.location_id, 'name'),
                    'location_dest_id': self._map_record(models, db, uid, password, 'stock.location', picking.location_dest_id, 'name'),
                }

                # Link to PO if exists
                if picking.purchase_id:
                    ext_po = models.execute_kw(
                        db, uid, password,
                        'purchase.order', 'search',
                        [[('name', '=', picking.purchase_id.name)]],
                        {'limit': 1}
                    )
                    if ext_po:
                        picking_vals['purchase_id'] = ext_po[0]

                # Link to SO if exists
                if picking.sale_id:
                    ext_so = models.execute_kw(
                        db, uid, password,
                        'sale.order', 'search',
                        [[('name', '=', picking.sale_id.name)]],
                        {'limit': 1}
                    )
                    if ext_so:
                        picking_vals['sale_id'] = ext_so[0]

                picking_ext_id = models.execute_kw(
                    db, uid, password,
                    'stock.picking', 'create', [picking_vals]
                )

                # Sync stock moves
                for move in picking.move_ids_without_package:
                    product_ext = self._map_product(models, db, uid, password, move.product_id)
                    uom_ext = self._map_record(models, db, uid, password, 'uom.uom', move.product_uom, 'name')
                    move_vals = {
                        'name': move.name,
                        'description_picking': move.description_picking,
                        'x_scanned_barcode': move.x_scanned_barcode,
                        'picking_id': picking_ext_id,
                        'product_id': product_ext,
                        'product_uom_qty': move.product_uom_qty,
                        'product_uom': move.product_uom.id,
                        'state': move.state,
                        'location_id': self._map_record(models, db, uid, password, 'stock.location', move.location_id, 'name'),
                        'location_dest_id': self._map_record(models, db, uid, password, 'stock.location', move.location_dest_id, 'name'),
                    }
                    models.execute_kw(db, uid, password, 'stock.move', 'create', [move_vals])

                for mline in picking.move_line_ids_without_package:
                    product_ext = self._map_product(models, db, uid, password, mline.product_id)
                    uom_ext = self._map_record(models, db, uid, password, 'uom.uom', mline.product_uom_id, 'name')

                    mline_vals = {
                        'description': mline.description,
                        'x_scanned_barcode': mline.x_scanned_barcode,
                        'picking_id': picking_ext_id,
                        'product_id': product_ext,
                        'qty_done': mline.qty_done,
                        'product_uom_id': uom_ext,
                        'location_id': self._map_record(models, db, uid, password, 'stock.location', mline.location_id, 'name'),
                        'location_dest_id': self._map_record(models, db, uid, password, 'stock.location', mline.location_dest_id, 'name'),
                        'move_id': self._map_record(models, db, uid, password, 'stock.move', mline.move_id, 'name'),
                    }
                    models.execute_kw(db, uid, password, 'stock.move.line', 'create', [mline_vals])


                _logger.info("Synced picking %s", picking.name)

            except Exception as e:
                _logger.error("Failed syncing picking %s: %s", picking.name, str(e))

    @api.model
    def _cron_sync_manufacturing_orders(self, models, db, uid, password, start_dt_utc, end_dt_utc):
        """Sync today's manufacturing orders to external DB."""
        mos = self.env['mrp.production'].search([
            ('create_date', '>=', start_dt_utc.strftime("%Y-%m-%d %H:%M:%S")),
            ('create_date', '<=', end_dt_utc.strftime("%Y-%m-%d %H:%M:%S")),
        ])
        _logger.info("Found %s manufacturing orders to sync", len(mos))

        for mo in mos:
            try:
                # --- Check if MO already exists ---
                existing = models.execute_kw(
                    db, uid, password,
                    'mrp.production', 'search',
                    [[('name', '=', mo.name)]],
                    {'limit': 1}
                )
                if existing:
                    mo_ext_id = existing[0]
                    _logger.info("MO %s already exists. Skipping header.", mo.name)
                else:
                    # --- Sync MO Header ---
                    mo_vals = {
                        'name': mo.name,
                        'x_scanned_barcode': mo.x_scanned_barcode,
                        'product_id': self._map_product(models, db, uid, password, mo.product_id),
                        'product_qty': float(mo.product_qty or 0.0),
                        'qty_producing': float(mo.qty_producing or 0.0),
                        'product_uom_id': self._map_record(models, db, uid, password, 'uom.uom', mo.product_uom_id, 'name'),
                        'date_planned_start': str(mo.date_planned_start) if mo.date_planned_start else False,
                        'date_planned_finished': str(mo.date_planned_finished) if mo.date_planned_finished else False,
                        'origin': mo.origin,
                        'state': mo.state,
                        'location_src_id': self._map_record(models, db, uid, password, 'stock.location', mo.location_src_id, 'name'),
                        'location_dest_id': self._map_record(models, db, uid, password, 'stock.location', mo.location_dest_id, 'name'),
                        'company_id': self._map_record(models, db, uid, password, 'res.company', mo.company_id, 'name'),
                        'bom_id': mo.bom_id.id,
                        'user_id': self._map_record(models, db, uid, password, 'res.users', mo.user_id, 'login') if mo.user_id else False,
                    }
                    mo_ext_id = models.execute_kw(db, uid, password, 'mrp.production', 'create', [mo_vals])
                    _logger.info("Synced new MO %s", mo.name)

                # --- Sync Raw Material Moves (Consumption) ---
                raw_moves = self.env['stock.move'].search([
                    ('raw_material_production_id', '=', mo.id),
                    ('write_date', '>=', start_dt_utc.strftime("%Y-%m-%d %H:%M:%S")),
                    ('write_date', '<=', end_dt_utc.strftime("%Y-%m-%d %H:%M:%S")),
                ])
                for move in raw_moves:
                    product_ext = self._map_product(models, db, uid, password, move.product_id)
                    if not product_ext:
                        continue
                    existing_move = models.execute_kw(
                        db, uid, password,
                        'stock.move', 'search',
                        [[
                            ('reference', '=', mo.name),
                            ('product_id', '=', product_ext),
                            ('product_uom', '=', move.product_uom.id),
                            ('x_scanned_barcode', '=', move.x_scanned_barcode or (move.product_id.barcode if move.product_id else False)),
                        ]],
                        {'limit': 1}
                    )

                    move_vals = {
                        'name': move.name,
                        'x_scanned_barcode': mo.x_scanned_barcode,
                        'reference': mo.name,
                        'raw_material_production_id': mo_ext_id,
                        'product_id': product_ext,
                        'product_uom_qty': float(move.product_uom_qty or 0.0),
                        'product_uom': move.product_uom.id,
                        'state': move.state,
                        'location_id': self._map_record(models, db, uid, password, 'stock.location', move.location_id, 'name'),
                        'location_dest_id': self._map_record(models, db, uid, password, 'stock.location', move.location_dest_id, 'name'),
                    }

                    if existing_move:
                        move_ext_id = existing_move[0]
                        models.execute_kw(db, uid, password, 'stock.move', 'write', [[move_ext_id], move_vals])
                    else:
                        move_ext_id = models.execute_kw(db, uid, password, 'stock.move', 'create', [move_vals])

                    # --- Sync Stock Move Lines ---
                    for line in move.move_line_ids:
                        existing_line = models.execute_kw(
                            db, uid, password,
                            'stock.move.line', 'search',
                            [[
                                ('move_id', '=', move_ext_id),
                                ('product_id', '=', product_ext),
                                ('product_uom_id', '=', line.product_uom_id.id),
                                ('x_scanned_barcode', '=', line.x_scanned_barcode or (line.product_id.barcode if line.product_id else False)),
                                ('lot_id', '=', line.lot_id.id if line.lot_id else False),
                            ]],
                            {'limit': 1}
                        )

                        line_vals = {
                            'move_id': move_ext_id,
                            'product_id': product_ext,
                            'qty_done': float(line.qty_done or 0.0),
                            'product_uom_id': self._map_record(models, db, uid, password, 'uom.uom', line.product_uom_id, 'name'),
                            'location_id': self._map_record(models, db, uid, password, 'stock.location', line.location_id, 'name'),
                            'location_dest_id': self._map_record(models, db, uid, password, 'stock.location', line.location_dest_id, 'name'),
                            'lot_id': self._map_record(models, db, uid, password, 'stock.lot', line.lot_id, 'name') if line.lot_id else False,
                        }
                        if existing_line:
                            models.execute_kw(db, uid, password, 'stock.move.line', 'write', [[existing_line[0]], line_vals])
                        else:
                            models.execute_kw(db, uid, password, 'stock.move.line', 'create', [line_vals])


                # --- Sync Stock Valuation Entries ---
                for move in mo.move_finished_ids.filtered(lambda m: m.state == 'done'):
                    for valuation in move.account_move_ids:
                        existing_am = models.execute_kw(
                            db, uid, password,
                            'account.move', 'search',
                            [[('ref', '=', valuation.ref), ('stock_move_id', '=', move.id)]],
                            {'limit': 1}
                        )
                        am_vals = {
                            'ref': valuation.ref,
                            'date': str(valuation.date),
                            'move_type': valuation.move_type,
                            'stock_move_id': move.id,
                            'company_id': self._map_record(models, db, uid, password, 'res.company', valuation.company_id, 'name'),
                            'line_ids': [(0, 0, {
                                'account_id': self._map_record(models, db, uid, password, 'account.account', line.account_id, 'code'),
                                'debit': float(line.debit or 0.0),
                                'credit': float(line.credit or 0.0),
                                'name': line.name,
                            }) for line in valuation.line_ids],
                        }
                        if existing_am:
                            models.execute_kw(db, uid, password, 'account.move', 'write', [[existing_am[0]], am_vals])
                        else:
                            models.execute_kw(db, uid, password, 'account.move', 'create', [am_vals])

                _logger.info("Synced MO %s successfully.", mo.name)

            except Exception as e:
                _logger.error("Failed syncing MO %s: %s", mo.name, str(e))

    @api.model
    def _cron_sync_bom_data(self, models, db, uid, password, start_dt_utc, end_dt_utc):
        """Sync Bill of Materials (BoM) to external DB within given date range."""

        boms = self.env['mrp.bom'].search([
            ('create_date', '>=', start_dt_utc.strftime("%Y-%m-%d %H:%M:%S")),
            ('create_date', '<=', end_dt_utc.strftime("%Y-%m-%d %H:%M:%S")),
        ])

        for bom in boms:
            # --- Sync Product Template ---
            product_tmpl_ext = False
            if bom.product_tmpl_id:
                # Call a dedicated template sync, not variant
                product_tmpl_ext = models.execute_kw(
                    db, uid, password, 'product.template', 'search',
                    [[('name', '=', bom.product_tmpl_id.name)]], {'limit': 1}
                )
                if isinstance(product_tmpl_ext, list):
                    product_tmpl_ext = product_tmpl_ext[0] if product_tmpl_ext else False

                if not product_tmpl_ext:
                    tmpl_vals = {
                        'name': bom.product_tmpl_id.name,
                        'uom_id': bom.product_tmpl_id.uom_id.id,
                        'uom_po_id': bom.product_tmpl_id.uom_po_id.id,
                        'type': bom.product_tmpl_id.type,
                    }
                    product_tmpl_ext = models.execute_kw(db, uid, password, 'product.template', 'create', [tmpl_vals])

            # --- Sync BoM Record ---
            bom_vals = {
                'code': bom.code or '',
                'x_scanned_barcode': bom.x_scanned_barcode,
                'product_tmpl_id': product_tmpl_ext,
                'product_qty': bom.product_qty,
                'product_uom_id': bom.product_uom_id.id,
                'type': bom.type,
            }

            # If BoM is product-specific, also map product
            if bom.product_id:
                product_ext = self._map_product(models, db, uid, password, bom.product_id)
                bom_vals['product_id'] = product_ext[0] if isinstance(product_ext, list) else product_ext

            # Check if BoM already exists in external DB
            domain = [('code', '=', bom.code or ''), ('product_tmpl_id', '=', product_tmpl_ext)]
            bom_ext = models.execute_kw(db, uid, password, 'mrp.bom', 'search', [domain])

            if isinstance(bom_ext, list):
                bom_ext = bom_ext[0] if bom_ext else False

            if bom_ext:
                models.execute_kw(db, uid, password, 'mrp.bom', 'write', [[bom_ext], bom_vals])
                bom_ext_id = bom_ext
            else:
                bom_ext_id = models.execute_kw(db, uid, password, 'mrp.bom', 'create', [bom_vals])

            # --- Sync BoM Lines ---
            for line in bom.bom_line_ids:
                product_ext = self._map_product(models, db, uid, password, line.product_id)
                product_ext_id = product_ext[0] if isinstance(product_ext, list) else product_ext

                line_vals = {
                    'x_scanned_barcode': line.x_scanned_barcode,
                    'name': line.name,
                    'bom_id': bom_ext_id,
                    'product_id': product_ext_id,
                    'product_qty': line.product_qty,
                    'product_uom_id': line.product_uom_id.id,
                }

                # Use product + UoM + barcode for uniqueness
                domain = [
                    ('bom_id', '=', bom_ext_id),
                    ('product_id', '=', product_ext_id),
                    ('product_uom_id', '=', line.product_uom_id.id),
                    ('x_scanned_barcode', '=', line.x_scanned_barcode or False),
                ]

                line_ext = models.execute_kw(db, uid, password, 'mrp.bom.line', 'search', [domain], {'limit': 1})

                if line_ext:
                    models.execute_kw(db, uid, password, 'mrp.bom.line', 'write', [[line_ext[0]], line_vals])
                else:
                    models.execute_kw(db, uid, password, 'mrp.bom.line', 'create', [line_vals])

    # ====================== _cron_sync_account_move =========== Dev X3
    @api.model
    def _cron_sync_account_move(self, models, db, uid, password, start_dt_utc, end_dt_utc):
        # 1. Search invoices in current DB
        account_moves = self.env['account.move'].search([
            ('move_type', 'in', ['out_invoice', 'out_refund', 'in_invoice', 'in_refund']),
            ('create_date', '>=', start_dt_utc.strftime("%Y-%m-%d %H:%M:%S")),
            ('create_date', '<=', end_dt_utc.strftime("%Y-%m-%d %H:%M:%S")),
        ])
        _logger.info("Found %s Account Move(s) to sync", len(account_moves))

        for move in account_moves:
            try:
                # 2. Check if already exists in remote DB
                existing_ids = models.execute_kw(
                    db, uid, password,
                    'account.move', 'search',
                    [[('name', '=', move.name)]],
                    {'limit': 1}
                )

                if existing_ids:
                    _logger.info("Invoice %s already exists in target DB. Skipping.", move.name)
                    continue

                # 3. Ensure partner exists (create if not)
                partner_ext_id = self._sync_partner(models, db, uid, password, move.partner_id)

                shipping_ext_id = self._sync_partner(models, db, uid, password, move.partner_shipping_id)

                # Sync journal
                journal_ext_id = self._map_journal(models, db, uid, password, move.journal_id)

                # Map invoice user
                invoice_user_ext_id = self._map_user(models, db, uid, password, move.invoice_user_id)

                # Map sales team
                team_ext_id = self._map_team(models, db, uid, password, move.team_id)

                # Map partner bank
                partner_bank_ext_id = self._map_partner_bank(models, db, uid, password, move.partner_bank_id)


                # 4. Prepare invoice data
                move_vals = {
                    'move_type': move.move_type,
                    'payment_state': move.payment_state,
                    'invoice_date': move.invoice_date or datetime.now().date().strftime("%Y-%m-%d"),
                    'invoice_issue_time': (datetime.combine(move.invoice_date, datetime.min.time()) if move.invoice_date else datetime.now()),
                    'invoice_date_due': move.invoice_date_due or move.invoice_date,
                    'partner_id': partner_ext_id,
                    'partner_shipping_id': shipping_ext_id,
                    'ref': move.ref,
                    'journal_id': journal_ext_id,
                    'partner_bank_id': partner_bank_ext_id,
                    'payment_reference': move.payment_reference,
                    'invoice_origin': move.invoice_origin,
                    'invoice_user_id': invoice_user_ext_id,
                    'team_id': team_ext_id,
                    'currency_id': self._map_currency(models, db, uid, password, move.currency_id),
                    'ref': move.ref or move.name,
                    'invoice_line_ids': self._prepare_invoice_lines(models, db, uid, password, move),
                }
                # 5. Create invoice in remote DB
                new_move_id = models.execute_kw(
                    db, uid, password,
                    'account.move', 'create',
                    [move_vals]
                )
                _logger.info("Created invoice %s in target DB (ID %s, draft)", move.name, new_move_id)

                # 6. Post the invoice only if it was posted in source DB
                if move.state == 'posted':
                    try:
                        models.execute_kw(
                            db, uid, password,
                            'account.move', 'action_post',
                            [[new_move_id]]
                        )
                        _logger.info("Posted invoice %s in target DB (because it was posted in source DB)", move.name)
                    except Exception as post_e:
                        _logger.error("Failed to post invoice %s: %s", move.name, str(post_e), exc_info=True)
                else:
                    _logger.info("Invoice %s remains draft in target DB (source state: %s)", move.name, move.state)

            except Exception as e:
                _logger.error("\n\n\n Failed to sync invoice %s: %s", move.name, str(e), exc_info=True)

    # ====================== _cron_sync_journal_entry =========== Dev X3
    @api.model
    def _cron_sync_journal_entry(self, models, db, uid, password, start_dt_utc, end_dt_utc):
        """Sync account moves (_cron_sync_journal_entry) between databases."""

        # 1. Search invoices in current DB
        account_moves = self.env['account.move'].search([
            ('move_type', 'in', ['entry']),
            ('create_date', '>=', start_dt_utc.strftime("%Y-%m-%d %H:%M:%S")),
            ('create_date', '<=', end_dt_utc.strftime("%Y-%m-%d %H:%M:%S")),
        ])
        _logger.info("Found %s Account Move(s) to sync", len(account_moves))

        for move in account_moves:
            try:
                # 2. Check if already exists in remote DB
                # existing_ids = models.execute_kw(
                #     db, uid, password,
                #     'account.move', 'search',
                #     [[('name', '=', move.name)]],
                #     {'limit': 1}
                # )
                existing_ids = models.execute_kw(
                    db, uid, password,
                    'account.move', 'search_read',
                    [[('name', '=', move.name)]],
                    {'fields': ['id', 'state'], 'limit': 1}
                )

                if existing_ids:
                    _logger.info("Invoice %s already exists in target DB. Skipping.", move.name)
                    continue

                # Sync journal
                journal_ext_id = self._map_journal(models, db, uid, password, move.journal_id)

                # 4. Prepare invoice data
                move_vals = {
                    'name' : move.name,
                    'move_type': move.move_type,
                    'date': move.invoice_date or datetime.now().date().strftime("%Y-%m-%d"),
                    'invoice_date': move.invoice_date or datetime.now().date().strftime("%Y-%m-%d"),
                    'invoice_issue_time': (datetime.combine(move.invoice_date, datetime.min.time()) if move.invoice_date else datetime.now()),
                    'journal_id': journal_ext_id,
                    'line_ids': self._prepare_je_lines(models, db, uid, password, move),
                }

                # 5. Create invoice in remote DB
                new_move_id = models.execute_kw(
                    db, uid, password,
                    'account.move', 'create',
                    [move_vals]
                )
                _logger.info("\n\n Created Journal Entry %s in target DB (ID %s, draft)", move.name, new_move_id)

                # Post the Journal Entry only if it was posted in source DB
                if move.state == 'posted':
                    try:
                        models.execute_kw(
                            db, uid, password,
                            'account.move', 'action_post',
                            [[new_move_id]]
                        )
                        _logger.info("Posted Journal Entry %s in target DB (because it was posted in source DB)", move.name)
                    except Exception as post_e:
                        _logger.error("Failed to post Journal Entry %s: %s", move.name, str(post_e), exc_info=True)
                else:
                    _logger.info("Invoice %s remains draft in target DB (source state: %s)", move.name, move.state)

            except Exception as e:
                _logger.error("\n\n\n Failed to sync Journal Entry %s: %s", move.name, str(e), exc_info=True)

    @api.model
    def _cron_sync_payments(self, models, db, uid, password, start_dt_utc, end_dt_utc):
        """Sync account payments between databases."""
        _logger.info("_cron_sync_payments started ")

        # 1. Search payments in current DB
        payments = self.env['account.payment'].search([
            ('create_date', '>=', start_dt_utc.strftime("%Y-%m-%d %H:%M:%S")),
            ('create_date', '<=', end_dt_utc.strftime("%Y-%m-%d %H:%M:%S")),
        ])
        _logger.info("Found %s Payment(s) to sync", len(payments))

        for payment in payments:
            try:
                # 2. Check if payment already exists in target DB
                existing_ids = models.execute_kw(
                    db, uid, password,
                    'account.payment', 'search_read',
                    [[('name', '=', payment.name)]],
                    {'fields': ['id', 'state'], 'limit': 1}
                )
                _logger.info("Checking existing payment %s: %s", payment.name, existing_ids)

                if existing_ids:
                    existing_payment = existing_ids[0]
                    if existing_payment['state'] == 'posted':
                        _logger.info("Payment %s already posted in target DB. Skipping.", payment.name)
                        continue
                    else:
                        _logger.info("Payment %s found in draft. Deleting old draft before sync.", payment.name)
                        # models.execute_kw(db, uid, password, 'account.payment', 'unlink', [[existing_payment['id']]])

                # 3. Map related records
                journal_ext_id = self._map_journal(models, db, uid, password, payment.journal_id)
                partner_ext_id = self._sync_partner(models, db, uid, password, payment.partner_id) if payment.partner_id else False
                partner_bank_ext_id = self._map_partner_bank(models, db, uid, password, payment.partner_bank_id) if payment.partner_bank_id else False
                currency_ext_id = self._map_currency(models, db, uid, password, payment.currency_id)
                destination_account_ext_id = self._map_account(models, db, uid, password, payment.destination_account_id) if payment.destination_account_id else False

                # 4. Prepare payment values
                payment_vals = {
                    'name': payment.name,
                    'journal_id': journal_ext_id,
                    'partner_type': payment.partner_type,
                    'payment_type': payment.payment_type,
                    'partner_id': partner_ext_id,
                    'destination_account_id': destination_account_ext_id,
                    'partner_bank_id': partner_bank_ext_id,
                    'currency_id': currency_ext_id,
                    'is_internal_transfer': payment.is_internal_transfer,
                    'amount': payment.amount,
                    'date': payment.date or fields.Date.today(),
                    'ref': payment.ref,
                    'payment_method_id': self._map_record(models, db, uid, password, 'account.payment.method', payment.payment_method_id, 'name') if payment.payment_method_id else False,
                }

                for xfield in ['x_studio_char_field_2ur2B', 'x_studio_char_field_cGBIG', 'x_studio_char_field_aIZX0', 'x_studio_char_field_W4FTm']:
                    if hasattr(payment, xfield):
                        payment_vals[xfield] = getattr(payment, xfield)

                # 5. Create payment in remote DB
                new_payment_id = models.execute_kw(
                    db, uid, password,
                    'account.payment', 'create',
                    [payment_vals]
                )
                # 6. Link payment to invoices (if any)
                _logger.info("\n\n------------------------->> Reconciled invoices: %s", payment.reconciled_invoice_ids)
                _logger.info("\n\n------------------------->> Reconciled invoices: %s", payment.reconciled_invoice_ids)
                if payment.reconciled_invoice_ids:
                    invoice_names = [name for name in payment.reconciled_invoice_ids.mapped('name') if name]
                    _logger.info("Invoice names to search in target: %s", invoice_names)

                    test_result = models.execute_kw(
                        db, uid, password,
                        'account.move', 'search_read',
                        [[('name', '=', invoice_names[0])]],
                        {'fields': ['id', 'name', 'move_type', 'company_id', 'create_uid']}
                    )
                    _logger.info("🔍 Test single invoice lookup result: %s", test_result)

                    target_invoice_ids = models.execute_kw(
                        db, uid, password,
                        'account.move', 'search_read',
                        [[('name', 'in', invoice_names), ('move_type', '=', 'out_invoice')]],
                        {'fields': ['id', 'name']}
                    )

                    _logger.info("✅ Target invoices found (filtered): %s", target_invoice_ids)


                    if target_invoice_ids:
                        _logger.info("Reconciling Payment %s with Invoices %s", payment.name, invoice_names)

                        # Reconcile payment and invoices in target DB
                        try:
                            # models.execute_kw(
                            #     db, uid, password,
                            #     'account.payment', 'action_post', [[new_payment_id]]
                            # )
                            # Perform reconciliation using register payment logic
                            # models.execute_kw(
                            #     db, uid, password,
                            #     'account.payment', 'reconcile_with_invoices',
                            #     [[new_payment_id], target_invoice_ids]
                            # )
                            # Step 1. Post the payment in target DB
                            ###################################################
                            models.execute_kw(
                                db, uid, password,
                                'account.payment', 'action_post', [[new_payment_id]]
                            )
                            #######################################################
                            # # Step 1: Clear name
                            # models.execute_kw(db, uid, password, 'account.payment', 'write', [[new_payment_id], {'name': 'DEMOTEST'}])

                            # # Step 2: Post payment
                            # models.execute_kw(db, uid, password, 'account.payment', 'action_post', [[new_payment_id]])

                            # # Step 3: Update name back (optional, won't break the journal)
                            # models.execute_kw(db, uid, password, 'account.payment', 'write', [[new_payment_id], {'name': payment.name}])

                            # Clear duplicate name before posting, then restore it after posting
                            # models.execute_kw(
                            #     db, uid, password,
                            #     'account.payment', 'write',
                            #     [[new_payment_id], {'name': False}]
                            # )
                            # models.execute_kw(db, uid, password, 'account.payment', 'action_post', [[new_payment_id]])

                            # # Optionally restore original payment name for traceability
                            # models.execute_kw(
                            #     db, uid, password,
                            #     'account.payment', 'write',
                            #     [[new_payment_id], {'name': payment.name}]
                            # )


                            # Step 2. Get move lines for payment and invoices
                            payment_move_lines = models.execute_kw(
                                db, uid, password,
                                'account.move.line', 'search_read',
                                [[
                                    ('payment_id', '=', new_payment_id),
                                    ('account_internal_type', 'in', ('receivable', 'payable')),
                                    ('reconciled', '=', False)
                                ]],
                                {'fields': ['id', 'account_id']}
                            )

                            invoice_move_lines = models.execute_kw(
                                db, uid, password,
                                'account.move.line', 'search_read',
                                [[
                                    ('move_id', 'in', target_invoice_ids),
                                    ('account_internal_type', 'in', ('receivable', 'payable')),
                                    ('reconciled', '=', False)
                                ]],
                                {'fields': ['id', 'account_id']}
                            )

                            if not payment_move_lines or not invoice_move_lines:
                                _logger.warning("No open move lines found for reconciliation: Payment %s", payment.name)
                            else:
                                # Step 3. Match by account and reconcile
                                account_ids = {line['account_id'][0] for line in payment_move_lines if line.get('account_id')}
                                for acc_id in account_ids:
                                    to_reconcile_ids = [
                                        line['id']
                                        for line in payment_move_lines + invoice_move_lines
                                        if line.get('account_id') and line['account_id'][0] == acc_id
                                    ]
                                    if to_reconcile_ids:
                                        try:
                                            recx = models.execute_kw(
                                                db, uid, password,
                                                'account.move.line', 'reconcile',
                                                [to_reconcile_ids]
                                            )
                                            _logger.info("Reconciled payment %s on account %s", payment.name, acc_id)
                                        except Exception as e:
                                            _logger.error("Failed to ----777---------reconcile payment %s: %s", payment.name, str(e))

                        except Exception as e:
                            _logger.error("Failed to reconcile Payment %s with invoices: %s", payment.name, str(e))


                        _logger.info("Created Payment %s (ID %s, draft) in target DB", payment.name, new_payment_id)

                # If original payment is posted, post it remotely
                # if payment.state == 'posted':
                #     models.execute_kw(db, uid, password, 'account.payment', 'action_post', [[new_payment_id]])
                #     _logger.info("Posted Payment %s (ID %s) in target DB", payment.name, new_payment_id)

            except Exception as e:
                _logger.error("Failed to sync Payment %s: %s", payment.name, str(e), exc_info=True)

    # ====================== _prepare_je_lines =========== Dev X3
    def _prepare_je_lines(self, models, db, uid, password, move):
        """
        Prepare the line_ids for a manual journal entry (move_type='entry')
        for syncing to the target DB.
        Returns a list of tuples in the format required by XML-RPC.
        """
        line_vals_list = []

        for line in move.line_ids:
            # Map accounts
            account_ext_id = self._map_account(models, db, uid, password, line.account_id)

            # Map analytic account (optional)
            analytic_ext_id = self._map_analytic_account(models, db, uid, password, line.analytic_account_id)

            # Map partner if present
            partner_ext_id = self._sync_partner(models, db, uid, password, line.partner_id) if line.partner_id else False

            # Map payment
            payment_ext_id = False
            if line.payment_id:
                existing_payment_ids = models.execute_kw(
                    db, uid, password,
                    'account.payment', 'search',
                    [[('name', '=', line.payment_id.name)]],
                    {'limit': 1}
                )
                if existing_payment_ids:
                    payment_ext_id = existing_payment_ids[0]
                else:
                    # If payment not in target DB, create via your payment sync method
                    _logger.warning("Payment %s linked to JE line not found in target DB. Consider syncing it first.", line.payment_id.name)

            line_vals = (0, 0, {
                'account_id': account_ext_id,
                'partner_id': partner_ext_id,
                'name':line.name,
                'analytic_account_id': analytic_ext_id,
                'tax_ids': [(6, 0, [
                            self._map_record(models, db, uid, password, 'account.tax', tax, 'name')
                            for tax in line.tax_ids
                        ])] if line.tax_ids else [],
                'debit': line.debit,
                'credit': line.credit,
                'payment_id': payment_ext_id,
            })

            # Improved logging
            _logger.info("\n\n Line Vals: %r", line_vals)
            line_vals_list.append(line_vals)

        _logger.info("\n\n Line Vals List: %r", line_vals_list)
        return line_vals_list

    # ==================== pos config ================ Dev X2
    @api.model
    def _cron_sync_pos_config_data(self, models, db, uid, password, start_dt_utc, end_dt_utc):
        """
        Sync POS Configs from Database A → Database B on cron.
        Includes updating ir.config_parameter so changes reflect in res.config.settings UI.
        """

        # Fetch configs in Database A between start/end datetime
        pos_configs = self.env['pos.config'].search([
            '|',
            ('create_date', '>=', start_dt_utc.strftime("%Y-%m-%d %H:%M:%S")),
            ('write_date', '>=', start_dt_utc.strftime("%Y-%m-%d %H:%M:%S")),
            ('create_date', '<=', end_dt_utc.strftime("%Y-%m-%d %H:%M:%S")),
            ('write_date', '<=', end_dt_utc.strftime("%Y-%m-%d %H:%M:%S")),
        ])
        _logger.info("Found %s POS Config records to sync", len(pos_configs))

        for config in pos_configs:
            try:
                _logger.info("Processing POS Config: %s", config.name)

                # Check if POS Config already exists in DB B
                existing = models.execute_kw(
                    db, uid, password,
                    'pos.config', 'search',
                    [[('name', '=', config.name)]],
                    {'limit': 1}
                )
                vals = {
                    'name': config.name,
                    'journal_id': self._map_record(models, db, uid, password, 'account.journal', config.journal_id,
                                                   'id'),
                    'invoice_journal_id': self._map_record(models, db, uid, password, 'account.journal',
                                                           config.invoice_journal_id, 'id'),
                    'company_id': self._map_record(models, db, uid, password, 'res.company', config.company_id, 'id'),
                    'sequence_id': self._map_record(models, db, uid, password, 'ir.sequence', config.sequence_id,
                                                    'name'),
                    'sequence_line_id': self._map_record(models, db, uid, password, 'ir.sequence',
                                                         config.sequence_line_id, 'name'),
                    'pricelist_id': self._map_record(models, db, uid, password, 'product.pricelist',
                                                     config.pricelist_id, 'name'),
                    'barcode_nomenclature_id': self._map_record(models, db, uid, password, 'barcode.nomenclature',
                                                                config.barcode_nomenclature_id, 'name'),
                    'iface_start_categ_id': self._map_record(models, db, uid, password, 'pos.category',
                                                             config.iface_start_categ_id, 'name'),
                    'tip_product_id': self._map_record(models, db, uid, password, 'product.product',
                                                       config.tip_product_id, 'name'),
                    'default_fiscal_position_id': self._map_record(models, db, uid, password, 'account.fiscal.position',
                                                                   config.default_fiscal_position_id, 'name'),
                    'default_cashbox_id': self._map_record(models, db, uid, password, 'account.cashbox',
                                                           config.default_cashbox_id, 'name'),
                    # 'rounding_journal_id': self._map_record(models, db, uid, password, 'account.journal',
                    #                                         config.rounding_journal_id, 'id'),
                    'loyalty_id': self._map_record(models, db, uid, password, 'loyalty.program', config.loyalty_id,
                                                   'name'),
                    'crm_team_id': self._map_record(models, db, uid, password, 'crm.team', config.crm_team_id, 'name'),
                    'discount_product_id': self._map_record(models, db, uid, password, 'product.product',
                                                            config.discount_product_id, 'name'),
                    'branch_id': self._map_record(models, db, uid, password, 'res.branch', config.branch_id, 'name'),
                    'receipt_header': config.receipt_header,
                    'receipt_footer': config.receipt_footer,
                    'sh_how_many_order_per_page': config.sh_how_many_order_per_page,
                    'module_pos_restaurant': config.module_pos_restaurant,
                    'manage_orders': config.manage_orders,
                    'iface_display_categ_images': config.iface_display_categ_images,
                    'pos_total_screen': config.pos_total_screen,
                    'limit_categories': config.limit_categories,
                    'start_category': config.start_category,
                    'iface_big_scrollbars': config.iface_big_scrollbars,
                    'sh_enable_order_list': config.sh_enable_order_list,
                    'sh_enable_re_order': config.sh_enable_re_order,
                    'sh_enable_order_reprint': config.sh_enable_order_reprint,
                    'is_posbox': config.is_posbox,
                    'other_devices': config.other_devices,
                    'tax_regime_selection': config.tax_regime_selection,
                    'tax_regime': config.tax_regime,
                    'is_cash_in_out': config.is_cash_in_out,
                    'is_print_statement': config.is_print_statement,
                    'use_pricelist': config.use_pricelist,
                    'iface_tax_included': config.iface_tax_included,
                    'module_pos_discount': config.module_pos_discount,
                    'manual_discount': config.manual_discount,
                    'module_pos_loyalty': config.module_pos_loyalty,
                    'restrict_price_control': config.restrict_price_control,
                    'cash_rounding': config.cash_rounding,
                    'cash_control': config.cash_control,
                    'amount_authorized_diff': config.amount_authorized_diff,
                    'iface_tipproduct': config.iface_tipproduct,
                    'pos_total_receipt': config.pos_total_receipt,
                    'is_header_or_footer': config.is_header_or_footer,
                    'iface_print_auto': config.iface_print_auto,
                    'module_account': config.module_account,
                    'enable_session_report': config.enable_session_report,
                    'enable_rounding': config.enable_rounding,
                    'rounding_options': config.rounding_options,
                    'iface_validate_close': config.iface_validate_close,
                    'iface_validate_decrease_quantity': config.iface_validate_decrease_quantity,
                    'iface_validate_delete_order': config.iface_validate_delete_order,
                    'iface_validate_delete_orderline': config.iface_validate_delete_orderline,
                    'iface_validate_discount': config.iface_validate_discount,
                    'iface_validate_payment': config.iface_validate_payment,
                    'iface_validate_price': config.iface_validate_price,
                    'rounding_journal_id': self._map_record(models, db, uid, password, 'pos.payment.method',
                                                            config.rounding_journal_id,
                                                            'id')
                }

                if existing:
                    config_ext_id = existing[0]
                    models.execute_kw(db, uid, password, 'pos.config', 'write',
                                      [[config_ext_id], vals])
                    _logger.info("Updated POS Config '%s' in DB ============B (ID %s)", config.name, config_ext_id)
                else:
                    config_ext_id = models.execute_kw(db, uid, password, 'pos.config', 'create', [vals])
                    _logger.info("Created POS Config '%s' in DB B (ID %s)", config.name, config_ext_id)

                # Update ir.config_parameter in DB B for Settings UI
                param_updates = {
                    'pos_receipt_header': config.receipt_header or "",
                    'pos_receipt_footer': config.receipt_footer or "",
                }

                for key, val in param_updates.items():
                    models.execute_kw(
                        db, uid, password,
                        'ir.config_parameter', 'set_param',
                        [key, val]
                    )
                    _logger.info("Updated ir.config_parameter '%s' in DB B to %s", key, val)

            except Exception as e:
                _logger.error("Failed syncing POS Confi================g %s: %s", config.name, str(e))

    # ==================== pos session, order ============= Dev X1
    @api.model
    def _cron_sync_pos_order_data(self, models, db, uid, password, start_dt_utc, end_dt_utc):
        """Sync POS Orders to external Odoo DB via XML-RPC"""
        pos_orders = self.env['pos.order'].search([
            ('date_order', '>=', start_dt_utc.strftime("%Y-%m-%d %H:%M:%S")),
            ('date_order', '<=', end_dt_utc.strftime("%Y-%m-%d %H:%M:%S")),
        ])
        _logger.info("Found %s POS orders to sync", len(pos_orders))

        for order in pos_orders:
            try:
                partner_ext_id = False

                # ------------------ Sync Order Header ------------------
                existing = models.execute_kw(
                    db, uid, password, 'pos.order', 'search',
                    [[('name', '=', order.name)]], {'limit': 1}
                )
                if existing:
                    order_ext_id = existing[0]
                else:
                    partner_ext_id = self._map_record(models, db, uid, password, 'res.partner', order.partner_id, 'name') if order.partner_id else False
                    session_ext_id = self._ensure_pos_session_remote(models, db, uid, password, order.session_id)

                    order_vals = {
                        'name': order.name,
                        'pos_reference': order.pos_reference,
                        'state': order.state,
                        'partner_id': partner_ext_id,
                        'date_order': str(order.date_order),
                        'amount_total': order.amount_total,
                        'amount_tax': order.amount_tax,
                        'amount_paid': order.amount_paid,
                        'amount_return': order.amount_return,
                        'session_id': session_ext_id,
                        'config_id': self._map_record(models, db, uid, password, 'pos.config', order.session_id.config_id, 'name'),
                        'user_id': self._map_record(models, db, uid, password, 'res.users', order.user_id, 'login'),
                        'company_id': self._map_record(models, db, uid, password, 'res.company', order.company_id, 'name'),
                    }
                    order_ext_id = models.execute_kw(db, uid, password, 'pos.order', 'create', [order_vals])

                # ------------------ Sync Lines ------------------
                for line in order.lines:
                    product_ext = self._map_product(models, db, uid, password, line.product_id)
                    product_ext_id = product_ext[0] if isinstance(product_ext, list) else product_ext
                    uom_ext_id = False
                    if line.uom_id:
                        uom_ext = self._map_record(models, db, uid, password, 'uom.uom', line.uom_id, 'name')
                        uom_ext_id = uom_ext[0] if isinstance(uom_ext, list) else uom_ext

                    domain = [('order_id', '=', order_ext_id), ('product_id', '=', product_ext_id)]
                    existing_line = models.execute_kw(db, uid, password, 'pos.order.line', 'search', [domain],
                                                      {'limit': 1})
                    if not existing_line:
                        line_vals = {
                            'order_id': order_ext_id,
                            'full_product_name': line.full_product_name,
                            'product_id': product_ext_id,
                            'name': line.name,
                            'qty': float(line.qty or 0.0),
                            'price_unit': float(line.price_unit or 0.0),
                            'discount': float(line.discount or 0.0),
                            'price_subtotal': float(line.price_subtotal or 0.0),
                            'price_subtotal_incl': float(line.price_subtotal_incl or 0.0),
                        }
                        if uom_ext_id:
                            line_vals['uom_id'] = uom_ext_id
                        models.execute_kw(db, uid, password, 'pos.order.line', 'create', [line_vals])

                # ------------------ Sync Payments ------------------
                self._sync_pos_payments(models, db, uid, password, order, order_ext_id)

                # ------------------ Sync Picking ------------------
                for picking in order.picking_ids:

                    # 1. Search for the existing picking by name
                    existing_picking = models.execute_kw(
                        db, uid, password, 'stock.picking', 'search',
                        [[('name', '=', picking.name)]], {'limit': 1}
                    )
                    
                    if existing_picking:
                        picking_id = existing_picking[0]
                        # 2. Read the current values of pos_session_id and pos_order_id
                        picking_data = models.execute_kw(
                            db, uid, password, 'stock.picking', 'read',
                            [[picking_id], ['pos_session_id', 'pos_order_id']]
                        )[0]

                        update_vals = {}
                        # 3. Check and prepare for updating pos_session_id
                        if not picking_data.get('pos_session_id'):
                            update_vals['pos_session_id'] = session_ext_id

                        # 4. Check and prepare for updating pos_order_id
                        if not picking_data.get('pos_order_id'):
                            update_vals['pos_order_id'] = order_ext_id

                        # 5. Perform the update if update_vals is not empty
                        if update_vals:
                            models.execute_kw(
                                db, uid, password, 'stock.picking', 'write', 
                                [[picking_id], update_vals]
                            )
                        else:
                            _logger.info("  -> No fields needed updating. Skipping write.")
                    else:
                        _logger.info(f"  -> WARNING: Picking '{picking.name}' not found in the database. Skipping.")

                # ------------------ Sync Invoice ------------------
                self._sync_invoice(models, db, uid, password, order, order_ext_id)


            except Exception as e:
                _logger.error("Failed syncing POS order %s: %s", order.name, str(e))

    #dev x1
    def _sync_invoice(self, models, db, uid, password, order, order_ext_id):
        if not order.to_invoice:
            return

        # 1. Check if invoice already exists
        existing_invoice = models.execute_kw(
            db, uid, password, 'account.move', 'search',
            [[('invoice_origin', '=', order.name)]],
            {'limit': 1}
        )
        if existing_invoice:
            invoice_id = existing_invoice[0]

            # Link invoice to POS order
            models.execute_kw(
                db, uid, password, 'pos.order', 'write',
                [[order_ext_id], {'account_move': invoice_id}]
            )
            return

        # 2. Map partner
        partner_ext_id = (
            self._map_record(models, db, uid, password, 'res.partner', order.partner_id, 'name')
            if order.partner_id else False
        )

        # 3. Build invoice lines
        invoice_lines = []
        for line in order.lines:
            product_ext_id = self._map_product(models, db, uid, password, line.product_id)
            product_ext_id = product_ext_id[0] if isinstance(product_ext_id, list) else product_ext_id

            tax_ext_ids = [
                self._map_record(models, db, uid, password, 'account.tax', t, 'name')
                for t in line.tax_ids_after_fiscal_position
            ] if line.tax_ids_after_fiscal_position else []

            invoice_lines.append({
                'name': line.name,
                'product_id': product_ext_id,
                'quantity': float(line.qty or 0.0),
                'price_unit': float(line.price_unit or 0.0),
                'tax_ids': [(6, 0, tax_ext_ids)] if tax_ext_ids else [],
            })

        # 4. Invoice values
        invoice_vals = {
            'move_type': 'out_invoice',
            'invoice_origin': order.name,
            'partner_id': partner_ext_id or False,
            'invoice_line_ids': [(0, 0, l) for l in invoice_lines],
            'currency_id': self._map_record(models, db, uid, password, 'res.currency',
                                            order.pricelist_id.currency_id, 'name'),
            'company_id': self._map_record(models, db, uid, password, 'res.company',
                                           order.company_id, 'name'),
            'invoice_date': str(order.date_order),
            'ref': order.pos_reference,
            'amount_total': float(order.amount_total),
        }

        # 5. Create invoice
        invoice_id = models.execute_kw(db, uid, password, 'account.move', 'create', [invoice_vals])

        # 6. Post invoice
        models.execute_kw(db, uid, password, 'account.move', 'action_post', [[invoice_id]])

        # 7. Link invoice to POS order
        models.execute_kw(
            db, uid, password, 'pos.order', 'write',
            [[order_ext_id], {'account_move': invoice_id}]
        )


    #dev x1
    def _ensure_pos_session_remote(self, models, db, uid, password, session):
        """Ensure POS session exists in remote DB and return its ID"""

        session_remote = models.execute_kw(
            db, uid, password, 'pos.session', 'search',
            [[('name', '=', session.name)]],
            {'limit': 1}
        )
        if session_remote:
            return session_remote[0]


        config_remote = self._map_record(
            models, db, uid, password, 'pos.config', session.config_id, 'name'
        )
        config_remote_id = config_remote[0] if isinstance(config_remote, list) else config_remote

        open_sessions = models.execute_kw(
            db, uid, password, 'pos.session', 'search',
            [[('config_id', '=', config_remote_id), ('state', '!=', 'closed')]],
            {'limit': 1}
        )
        if open_sessions:
            return open_sessions[0]

        # compute picking count locally (from this session’s orders)
        all_pickings = session.order_ids.mapped('picking_ids')
        picking_count = len(all_pickings)
        failed_pickings = bool(all_pickings.filtered(lambda p: p.state != 'done'))

        session_vals = {
            'name': session.name,
            'config_id': config_remote_id,
            'user_id': self._map_record(models, db, uid, password, 'res.users', session.user_id, 'login'),
            'state': session.state,  # preserve state from local
            'start_at': str(session.start_at) if session.start_at else False,
            'stop_at': str(session.stop_at) if session.stop_at else False,
        }

        # create session in receiver DB
        session_id = models.execute_kw(
            db, uid, password,
            'pos.session', 'create',
            [session_vals]
        )

        # ensure remote session name matches sender sequence
        models.execute_kw(
            db, uid, password,
            'pos.session', 'write',
            [[session_id], {
                'name': session.name,
                'picking_count': picking_count,
                'failed_pickings': failed_pickings,
            }]
        )

        return session_id

    #dev x1
    def _sync_pos_payments(self, models, db, uid, password, order, order_ext_id):
        """Sync POS Payments for a given order and validate against receiver"""
        try:
            # Get existing payments from receiver
            existing_payments = models.execute_kw(
                db, uid, password,
                'pos.payment', 'search_read',
                [[('pos_order_id', '=', order_ext_id)]],
                {'fields': ['id', 'payment_method_id', 'amount', 'payment_date', 'name']}
            )
            existing_map = {
                (p['payment_method_id'][0], float(p['amount']), p['payment_date']): p
                for p in existing_payments
            }

            # Ensure we have the correct session for the order
            remote_session_id = self._ensure_pos_session_remote(models, db, uid, password, order.session_id)

            # Read remote session to get config
            remote_session = models.execute_kw(
                db, uid, password,
                'pos.session', 'read',
                [remote_session_id],
                {'fields': ['config_id']}
            )[0]
            remote_config_id = remote_session['config_id'][0]

            for payment in order.payment_ids:
                # Map payment method from local → remote
                method_ext = self._map_record(
                    models, db, uid, password,
                    'pos.payment.method', payment.payment_method_id, 'name'
                )
                method_ext_id = method_ext[0] if isinstance(method_ext, list) else method_ext

                # Ensure payment method is allowed in remote config
                config = models.execute_kw(
                    db, uid, password,
                    'pos.config', 'read',
                    [remote_config_id],
                    {'fields': ['payment_method_ids']}
                )[0]

                if method_ext_id not in config['payment_method_ids']:
                    models.execute_kw(
                        db, uid, password,
                        'pos.config', 'write',
                        [[remote_config_id], {'payment_method_ids': [(4, method_ext_id)]}]
                    )

                key = (method_ext_id, float(payment.amount), str(payment.payment_date))

                if key in existing_map:
                    # Payment already exists remotely → skip
                    continue

                # If not exists → create new payment
                payment_vals = {
                    'pos_order_id': order_ext_id,
                    'payment_method_id': method_ext_id,
                    'amount': float(payment.amount),
                    'payment_date': str(payment.payment_date),
                    'session_id': remote_session_id,
                    'name': payment.name,
                }
                payment_ext_id = models.execute_kw(
                    db, uid, password, 'pos.payment', 'create', [payment_vals]
                )

        except Exception as pe:
            _logger.error("Failed syncing payments for POS order %s: %s", order.name, str(pe))

    # ====================== _sync_partner =========== Dev X3
    def _sync_partner(self, models, db, uid, password, partner):
        """Ensure partner exists in target DB, create if missing."""
        if not partner:
            return False
        existing = models.execute_kw(
            db, uid, password,
            'res.partner', 'search',
            [[('name', '=', partner.name)]], {'limit': 1}
        )
        if existing:
            return existing[0]
        return models.execute_kw(
            db, uid, password,
            'res.partner', 'create',
            [{
                'name': partner.name,
                'street': partner.street,
                'city': partner.city,
                'phone': partner.phone,
                'email': partner.email,
            }]
        )

    # ====================== _prepare_invoice_lines =========== Dev X3
    def _prepare_invoice_lines(self, models, db, uid, password, move):
        """Prepare invoice line values with product + account mapping."""
        line_vals = []
        for line in move.invoice_line_ids:
            product_ext_id = False
            if line.product_id:
                product_ext_id = self._map_product(models, db, uid, password, line.product_id)
            uom_ext_id = self._map_uom(models, db, uid, password, line.product_uom_id)
            packaging_ext_id = self._map_packaging(models, db, uid, password, line.product_packaging_id)
            analytic_ext_id = self._map_analytic_account(models, db, uid, password, line.analytic_account_id)

            line_vals.append((0, 0, {
                'name': line.name,
                'product_id': product_ext_id,
                'quantity': line.quantity,
                'price_unit': line.price_unit,
                'discount': line.discount,
                'product_packaging_id': packaging_ext_id,
                'product_packaging_qty': line.product_packaging_qty,
                'analytic_account_id': analytic_ext_id,
                'price_subtotal': line.price_subtotal,
                'product_uom_id': uom_ext_id,
                'tax_ids': [(6, 0, [
                            self._map_record(models, db, uid, password, 'account.tax', tax, 'name')
                            for tax in line.tax_ids
                        ])] if line.tax_ids else [],
            }))
        return line_vals

    # -------------------------------
    # Helpers
    # -------------------------------

    def _map_currency(self, models, db, uid, password, currency):
        """Map currency by name/code (fallback to company currency)."""
        if not currency:
            return False
        existing = models.execute_kw(
            db, uid, password,
            'res.currency', 'search',
            [[('name', '=', currency.name)]], {'limit': 1}
        )
        return existing[0] if existing else False

    def _map_record(self, models, db, uid, password, model, record, search_field='name', extra_vals=None):
        if not record:
            return False
        ext_id = models.execute_kw(
            db, uid, password,
            model, 'search',
            [[(search_field, '=', getattr(record, search_field))]],
            {'limit': 1}
        )
        if ext_id:
            return ext_id[0]
        vals = {search_field: getattr(record, search_field)}
        if extra_vals:
            vals.update(extra_vals)
        return models.execute_kw(db, uid, password, model, 'create', [vals])

    
    def _map_picking(self, models, db, uid, password, picking, partner_ext, origin, order_ext_id=None, po_ext_id=None):
        """Ensure picking is unique and mapped, don't create duplicates."""
        if not picking:
            return False

        ext_id = models.execute_kw(
            db, uid, password,
            'stock.picking', 'search',
            [[('name', '=', picking.name)]],
            {'limit': 1}
        )
        if ext_id:
            _logger.info("Picking %s already exists, reusing ID %s", picking.name, ext_id[0])
            return ext_id[0]

        picking_vals = {
            'name': picking.name,
            'origin': origin,
            'partner_id': partner_ext,
            'picking_type_id': self._map_record(models, db, uid, password, 'stock.picking.type', picking.picking_type_id, 'name'),
            'scheduled_date': str(picking.scheduled_date) if picking.scheduled_date else False,
            'state': picking.state,
        }
        if order_ext_id:
            picking_vals['sale_id'] = order_ext_id
        if po_ext_id:
            picking_vals['purchase_id'] = po_ext_id

        picking_ext_id = models.execute_kw(db, uid, password, 'stock.picking', 'create', [picking_vals])
        _logger.info("Created new picking %s", picking.name)
        return picking_ext_id

    # ====================== _map_product =========== Dev X3
    def _map_product(self, models, db, uid, password, product):
        if not product:
            return False
        if product.barcode:
            ext_id = models.execute_kw(
                db, uid, password,
                'product.product', 'search',
                [[('barcode', '=', product.barcode)]],
                {'limit': 1}
            )
            return ext_id[0] if ext_id else False
        return False

    # ====================== _map_account =========== Dev X3
    def _map_account(self, models, db, uid, password, account):
        if not account:
            return False
        ext_id = models.execute_kw(
            db, uid, password,
            'account.account', 'search',
            [[('code', '=', account.code)]],
            {'limit': 1}
        )
        return ext_id[0] if ext_id else False

    # ====================== _map_journal =========== Dev X3
    def _map_journal(self, models, db, uid, password, journal):
        """Map account.journal by code or name."""
        if not journal:
            return False
        existing = models.execute_kw(
            db, uid, password,
            'account.journal', 'search',
            [[('code', '=', journal.code)]], {'limit': 1}
        )
        if existing:
            return existing[0]
        # fallback create (basic info)
        return models.execute_kw(
            db, uid, password,
            'account.journal', 'create',
            [{
                'name': journal.name,
                'code': journal.code,
                'type': journal.type,
            }]
        )

    # ====================== _map_uom_category =========== Dev X3
    def _map_uom_category(self, models, db, uid, password, category):
        if not category:
            return False
        existing = models.execute_kw(
            db, uid, password,
            'uom.category', 'search',
            [[('name', '=', category.name)]], {'limit': 1}
        )
        if existing:
            return existing[0]
        return models.execute_kw(
            db, uid, password,
            'uom.category', 'create',
            [{'name': category.name}]
        )

    # ====================== _map_uom =========== Dev X3
    def _map_uom(self, models, db, uid, password, uom):
        """Map product.uom by name."""

        category_ext_id = self._map_uom_category(models, db, uid, password, uom.category_id)

        if not uom:
            return False
        existing = models.execute_kw(
            db, uid, password,
            'uom.uom', 'search',
            [[('name', '=', uom.name), ('category_id', '=', category_ext_id)]],
            {'limit': 1}
        )
        if existing:
            return existing[0]
        # fallback create (basic info)
        return models.execute_kw(
            db, uid, password,
            'uom.uom', 'create',
            [{
                'name': uom.name,
                'category_id': category_ext_id,
                'uom_type': uom.uom_type,
                'factor_inv': uom.factor_inv,
                'rounding': uom.rounding,
            }]
        )

    # ====================== _map_packaging =========== Dev X3
    def _map_packaging(self, models, db, uid, password, packaging):
        """Map product.packaging by name + product."""
        if not packaging:
            return False
        existing = models.execute_kw(
            db, uid, password,
            'product.packaging', 'search',
            [[('name', '=', packaging.name)]], {'limit': 1}
        )
        if existing:
            return existing[0]
        # fallback create (basic info)
        return models.execute_kw(
            db, uid, password,
            'product.packaging', 'create',
            [{
                'name': packaging.name,
                'product_id': self._map_product(models, db, uid, password, packaging.product_id) if packaging.product_id else False,
                'qty': packaging.qty,
                'barcode': packaging.barcode,
            }]
        )

    # ====================== _map_analytic_account =========== Dev X3
    def _map_analytic_account(self, models, db, uid, password, analytic):
        """Map account.analytic.account by name."""
        if not analytic:
            return False
        existing = models.execute_kw(
            db, uid, password,
            'account.analytic.account', 'search',
            [[('name', '=', analytic.name)]], {'limit': 1}
        )
        if existing:
            return existing[0]
        # fallback create
        return models.execute_kw(
            db, uid, password,
            'account.analytic.account', 'create',
            [{
                'name': analytic.name,
                'code': analytic.code or analytic.name.replace(" ", "_"),
                'active': analytic.active,
            }]
        )

    # ====================== _map_user =========== Dev X3
    def _map_user(self, models, db, uid, password, user):
        """Map res.users by login or name."""
        if not user:
            return False
        existing = models.execute_kw(
            db, uid, password,
            'res.users', 'search',
            [[('login', '=', user.login)]], {'limit': 1}
        )
        if existing:
            return existing[0]
        # fallback create minimal user (optional, usually better to skip if user missing)
        return models.execute_kw(
            db, uid, password,
            'res.users', 'create',
            [{
                'name': user.name,
                'login': user.login,
            }]
        )

    # ====================== _map_team =========== Dev X3
    def _map_team(self, models, db, uid, password, team):
        """Map crm.team by name."""
        if not team:
            return False
        existing = models.execute_kw(
            db, uid, password,
            'crm.team', 'search',
            [[('name', '=', team.name)]], {'limit': 1}
        )
        if existing:
            return existing[0]
        # fallback create minimal team
        return models.execute_kw(
            db, uid, password,
            'crm.team', 'create',
            [{
                'name': team.name,
            }]
        )

    # ====================== _map_partner_bank =========== Dev X3
    def _map_partner_bank(self, models, db, uid, password, bank):
        """Map res.partner.bank by account number and partner."""
        if not bank:
            return False

        # Ensure partner exists first
        partner_ext_id = self._sync_partner(models, db, uid, password, bank.partner_id) if bank.partner_id else False

        existing = models.execute_kw(
            db, uid, password,
            'res.partner.bank', 'search',
            [[('acc_number', '=', bank.acc_number), ('partner_id', '=', partner_ext_id)]],
            {'limit': 1}
        )
        if existing:
            return existing[0]

        # fallback create
        return models.execute_kw(
            db, uid, password,
            'res.partner.bank', 'create',
            [{
                'acc_number': bank.acc_number,
                'partner_id': partner_ext_id,
                'bank_id': self._map_bank(models, db, uid, password, bank.bank_id),
                'currency_id': self._map_currency(models, db, uid, password, bank.currency_id),
            }]
        )

    # ====================== _map_bank =========== Dev X3
    def _map_bank(self, models, db, uid, password, bank):
        """Map res.bank by BIC or name."""
        if not bank:
            return False
        existing = models.execute_kw(
            db, uid, password,
            'res.bank', 'search',
            [[('bic', '=', bank.bic)]], {'limit': 1}
        )
        if existing:
            return existing[0]

        # fallback create minimal bank
        return models.execute_kw(
            db, uid, password,
            'res.bank', 'create',
            [{
                'name': bank.name,
                'bic': bank.bic,
            }]
        )

    def _map_lot(self, models, db, uid, password, lot):
        """Map or create stock.lot safely (product + lot name)"""
        if not lot:
            return False
        try:
            domain = [('name', '=', lot.name)]
            if lot.product_id:
                domain.append(('product_id.name', '=', lot.product_id.name))
            res = models.execute_kw(db, uid, password, 'stock.lot', 'search', [domain], {'limit': 1})
            if res:
                return res[0]

            vals = {
                'name': lot.name,
                'product_id': self._map_record(models, db, uid, password, 'product.product', lot.product_id, 'name'),
            }
            new_id = models.execute_kw(db, uid, password, 'stock.lot', 'create', [vals])
            _logger.info("Created new lot %s for product %s", lot.name, lot.product_id.display_name)
            return new_id
        except Exception as e:
            _logger.error("Error mapping lot %s: %s", lot.name, str(e))
            return False