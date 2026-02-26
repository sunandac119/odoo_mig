import os
import json
from datetime import datetime
from odoo import models, fields, _
from odoo.exceptions import UserError
import logging

_logger = logging.getLogger(__name__)

class AccountMove(models.Model):
    _inherit = 'account.move'

    def action_export_json(self):
        for move in self:
            data = {
                "DocNo": move.name,
                "DocDate": str(move.invoice_date or ""),
                "DebtorCode": move.partner_id.debtor_code or "",
                "Description": move.narration or "",
                "SalesAgent": move.user_id.name or "",
                "Details": [{
                    "AccNo": move.line_ids.filtered(lambda l: not l.exclude_from_invoice_tab and l.account_id).mapped(
                        'account_id')[0].code or "",
                    "ProjNo": "",
                    "Amount": move.amount_total
                }]
            }


            json_data = json.dumps(data, indent=4)

            home_dir = os.path.expanduser("~")
            year = str(move.invoice_date.year if move.invoice_date else datetime.today().year)
            month = f"{move.invoice_date.month:02d}" if move.invoice_date else f"{datetime.today().month:02d}"
            export_dir = os.path.join(home_dir, "Documents")
            os.makedirs(export_dir, exist_ok=True)  # ✅ Ensure full path exists

            safe_filename = f"{move.name.replace('/', '_')}.json"
            file_path = os.path.join(export_dir, safe_filename)

            try:
                with open(file_path, "w", encoding="utf-8") as f:
                    f.write(json_data)
                _logger.info(f"Invoice JSON saved to: {file_path}")
            except Exception as e:
                _logger.error(f"Error writing JSON file: {e}")
                raise UserError(_("Failed to save file: %s") % str(e))

            return {
                'type': 'ir.actions.client',
                'tag': 'display_notification',
                'params': {
                    'title': _('JSON Exported'),
                    'message': f'File saved to:\n{file_path}',
                    'type': 'success',
                    'sticky': False,
                }
            }


class ResPartner(models.Model):
    _inherit = 'res.partner'

    debtor_code = fields.Char(string="Debtor Code")
