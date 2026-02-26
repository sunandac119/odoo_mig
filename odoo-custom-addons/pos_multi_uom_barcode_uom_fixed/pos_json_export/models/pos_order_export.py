import os
import json
from odoo import models, fields, _
from odoo.exceptions import UserError
from datetime import datetime, timedelta
import logging

_logger = logging.getLogger(__name__)

class PosOrder(models.Model):
    _inherit = 'pos.order'

    def action_export_pos_sales_json(self, export_date=False):
        export_date = fields.Date.from_string(export_date) if export_date else fields.Date.today()

        pos_orders = self.search([
            ('state', '=', 'done'),
        ])

        if not pos_orders:
            raise UserError(_("No POS orders found for the date %s") % export_date)

        home_dir = os.path.expanduser("~")
        dir_path = os.path.join(home_dir, "Documents", "pos_json_exports")
        os.makedirs(dir_path, exist_ok=True)

        for order in pos_orders:
            partner = order.partner_id
            journal = order.account_move.journal_id

            if not partner.debtor_code:
                raise UserError(_("Debtor Code missing for partner %s.") % partner.name)

            details = []
            payments = {}

            for line in order.lines:
                details.append({
                    "ItemCode": line.product_id.default_code or "",
                    "Description": line.product_id.name or "",
                    "ProjNo": order.session_id.config_id.name or "",
                    "Qty": line.qty,
                    "UnitPrice": line.price_unit,
                    "SubTotal": line.price_subtotal
                })

            for payment in order.payment_ids:
                pm = payment.payment_method_id.name
                payments[pm] = payments.get(pm, 0.0) + payment.amount

            payment_list = [
                {"PaymentMethod": method, "PaymentAmt": round(amount, 2)}
                for method, amount in payments.items()
            ]

            doc_no = f"CS-{order.name.replace('/', '')}"
            record = {
                "DocNo": doc_no,
                "DocDate": str(export_date),
                "DebtorCode": partner.debtor_code,
                "SalesAgent": "",
                "Details": details,
                "PaymentDetails": payment_list
            }

            # Write to file
            json_output = json.dumps(record, indent=4)
            # timestamp = datetime.now().strftime('%Y%m%d%H')  # No underscore between date and hour
            timestamp = fields.Datetime.context_timestamp(self, fields.Datetime.now()).strftime('%Y%m%d%H')
            file_name = f"{doc_no}_{timestamp}.json"
            #file_name = f"{doc_no}_{export_date.strftime('%Y%m%d')}.json"
            file_path = os.path.join(dir_path, file_name)

            try:
                with open(file_path, 'w', encoding='utf-8') as f:
                    f.write(json_output)
                _logger.info(f"Exported POS JSON to {file_path}")
            except Exception as e:
                _logger.error(f"Failed to write JSON for {doc_no}: {str(e)}")
                raise UserError(_("Failed to export POS JSON for %s: %s") % (doc_no, str(e)))

        return {
            'type': 'ir.actions.client',
            'tag': 'display_notification',
            'params': {
                'title': _('POS Export Completed'),
                'message': _('Individual JSON files saved in ~/Documents/pos_json_exports'),
                'type': 'success',
                'sticky': False
            }
        }

    # def action_export_pos_sales_json(self, export_date=False):
    #     export_date = fields.Date.from_string(export_date) if export_date else fields.Date.today()
    #
    #     pos_orders = self.search([
    #         ('state', '=', 'done'),
    #     ])
    #
    #     print('pos_orders',pos_orders)
    #
    #     if not pos_orders:
    #         raise UserError(_("No POS orders found for the date %s") % export_date)
    #
    #     grouped = {}
    #     for order in pos_orders:
    #         journal = order.account_move.journal_id
    #         key = (journal.id, order.partner_id.id)
    #         grouped.setdefault(key, []).append(order)
    #
    #     final_data = []  # Store all grouped records here
    #
    #     for (journal_id, partner_id), orders in grouped.items():
    #         partner = self.env['res.partner'].browse(partner_id)
    #         journal = self.env['account.journal'].browse(journal_id)
    #
    #         if not partner.debtor_code:
    #             raise UserError(_("Debtor Code missing for partner %s.") % partner.name)
    #
    #         details = []
    #         payments = {}
    #
    #         for order in orders:
    #             for line in order.lines:
    #                 details.append({
    #                     "ItemCode": line.product_id.default_code or "",
    #                     "Description": line.product_id.name or "",
    #                     "ProjNo": order.session_id.config_id.name or "",
    #                     "Qty": line.qty,
    #                     "UnitPrice": line.price_unit,
    #                     "SubTotal": line.price_subtotal
    #                 })
    #
    #             for payment in order.payment_ids:
    #                 pm = payment.payment_method_id.name
    #                 payments[pm] = payments.get(pm, 0.0) + payment.amount
    #
    #         payment_list = [
    #             {"PaymentMethod": method, "PaymentAmt": round(amount, 2)}
    #             for method, amount in payments.items()
    #         ]
    #
    #         doc_no = f"CS-{orders[0].name.replace('/', '')}"
    #         record = {
    #             "DocNo": doc_no,
    #             "DocDate": str(export_date),
    #             "DebtorCode": partner.debtor_code,
    #             "SalesAgent": "",
    #             "Details": details,
    #             "PaymentDetails": payment_list
    #         }
    #
    #         final_data.append(record)
    #
    #     # Save all grouped records to one file
    #     json_output = json.dumps(final_data, indent=4)
    #
    #     home_dir = os.path.expanduser("~")
    #     dir_path = os.path.join(home_dir, "Documents", "pos_json_exports")
    #     os.makedirs(dir_path, exist_ok=True)
    #
    #     file_name = f"POS_SALES_{export_date.strftime('%Y%m%d')}.json"
    #     file_path = os.path.join(dir_path, file_name)
    #
    #     try:
    #         with open(file_path, 'w', encoding='utf-8') as f:
    #             f.write(json_output)
    #         _logger.info(f"Exported POS JSON to {file_path}")
    #     except Exception as e:
    #         _logger.error(f"Failed to write JSON: {str(e)}")
    #         raise UserError(_("Failed to export POS JSON: %s") % str(e))
    #
    #     return {
    #         'type': 'ir.actions.client',
    #         'tag': 'display_notification',
    #         'params': {
    #             'title': _('POS Export Completed'),
    #             'message': _('JSON file saved in ~/Documents/pos_json_exports'),
    #             'type': 'success',
    #             'sticky': False
    #         }
    #     }
