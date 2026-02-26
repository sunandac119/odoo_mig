from odoo import api, fields, models, _
import requests
import json
from odoo.exceptions import MissingError, ValidationError, AccessError, UserError
import paramiko
from odoo.osv import expression
import logging

_logger = logging.getLogger("yashh====>")

PEPPOL_INVOICE_TYPE_CODE = {
    '380': 'out_invoice',
    '381': 'out_refund',
    '380': 'in_invoice',
    '381': 'in_refund'
}

SFTP_AI_DOCUMENTS_TYPE_CODE = {
    "Invoice":"out_invoice",
    "CreditNote":"out_refund",
    "DebitNote":"out_invoice"
}


class LhdnSetup(models.Model):
    _name = 'lhdn.setup'
    _description = 'LhdnSetup'

    api_subscription_type = fields.Selection([
        ('peppol_api', 'Peppol API'),
        ('myinvoice_api', 'MyInvoice API')],
        string="Subscription Type")

    api_subscription_status = fields.Selection([
        ('active', 'Active'),
        ('non_active', 'Non-Active'),
        ('warning', 'Warning'),
        ('payment_issue', 'Payment Issue')
    ], string="Subscription status")
    peppol_credit = fields.Float(string="Peppol Credit")
    peppol_sync_api_client_id = fields.Char(string="Peppol Sync API Client Id")
    peppol_sync_api_client_password = fields.Char(string="Peppol Sync API Client Password")
    peppol_sync_api_base_url = fields.Char(string="Peppol Sync API Base url")
    my_company_msic_code_id = fields.Many2one('lhdn.msic.code', string="My Company MSIC Code")
    msic_code_import_url = fields.Char(string="MSIC Code Url",
                                       default="https://sdk.myinvois.hasil.gov.my/files/MSICSubCategoryCodes.json")
    item_classification_code_url = fields.Char(string="Item Classification Url",
                                               default="https://sdk.myinvois.hasil.gov.my/files/ClassificationCodes.json")
    malaysian_states_code_url = fields.Char(string="Malaysian Country States code Url",
                                            default="https://sdk.myinvois.hasil.gov.my/files/StateCodes.json")

    lhdn_api_client_id = fields.Char(string="LHDN API Client Id")
    lhdn_api_client_password = fields.Char(string="LHDN API Client Password")
    choose_submission_way = fields.Selection([('direct_api', 'Direct API'), ('intermediate_api', 'Intermediate API')],
                                             string="Choose Submission way", default='intermediate_api')
    lhdn_connection_server_type = fields.Selection([('sandbox', 'Sandbox'), ('production', 'Production')],
                                                   string="LHDN Server Type", default='sandbox')
    lhdn_sandbox_base_url = fields.Char(string="LHDN Sandbox URL", default='https://preprod-api.myinvois.hasil.gov.my')
    lhdn_production_base_url = fields.Char(string="LHDN Production URL", default='https://api.myinvois.hasil.gov.my')
    lhdn_token = fields.Char(string="LHDN Token")
    lhdn_token_updateds_time = fields.Datetime(string="Last LHDN Token Updated Time")
    create_invoice_using_sftp_server = fields.Boolean(string="Create Invoice Usings SFTP Server?")
    sftp_server_ip = fields.Char(string="SFTP Server IP")
    sftp_server_user = fields.Char(string="SFTP Server User Name")
    sftp_server_passwords = fields.Char(string="SFTP Server Password")

    def test_lhdn_api_connection(self):
        headers = {'Content-Type': 'application/json'}
        data = {
            'api_client_id': self.peppol_sync_api_client_id,
            'api_client_password': self.peppol_sync_api_client_password
        }
        _logger.info(f'{self.peppol_sync_api_base_url}/v1/my_status')
        res = requests.post(f'{self.peppol_sync_api_base_url}/v1/my_status', params=json.dumps(data), headers=headers)
        try:
            res.json()
        except:
            return {
                'type': 'ir.actions.client',
                'tag': 'display_notification',
                'params': {
                    'type': 'danger',
                    'message': _("Error occurings during send the post request"),
                    'next': {'type': 'ir.actions.act_window_close'},
                }
            }
        message = "Not setup correctly"
        message_type = 'danger'
        if res.status_code == 200:
            # res = res.json()
            message = "Your API was successfully setup"
            message_type = 'success'
        return {
            'type': 'ir.actions.client',
            'tag': 'display_notification',
            'params': {
                'type': message_type,
                'message': _(f"{message}"),
                'next': {'type': 'ir.actions.act_window_close'},
            }
        }

    def import_msic_code(self):
        if not self.msic_code_import_url:
            raise UserError(_('Enter the Url'))
        self.env['lhdn.msic.code'].search([]).unlink()
        response = requests.get(self.msic_code_import_url)
        if response.status_code == 200:
            response_dict = response.json()
            msic_code_dict = []
            for rec in response_dict:
                msic_code_dict.append({'name': rec.get('Description'), 'code': rec.get('Code')})
            if msic_code_dict:
                self.env['lhdn.msic.code'].sudo().create(msic_code_dict)
        else:
            raise UserError(_(response))

    def import_item_classification_code(self):
        if not self.item_classification_code_url:
            raise UserError(_('Enter the Url'))
        self.env['lhdn.item.classification.code'].search([]).unlink()
        response = requests.get(self.item_classification_code_url)
        if response.status_code == 200:
            response_dict = response.json()
            msic_code_dict = []
            for rec in response_dict:
                msic_code_dict.append({'name': rec.get('Description'), 'code': rec.get('Code')})
            if msic_code_dict:
                self.env['lhdn.item.classification.code'].sudo().create(msic_code_dict)
        else:
            raise UserError(_(response))

    def import_malaysian_states_code(self):
        if not self.malaysian_states_code_url:
            raise UserError(_('Enter the Url'))
        self.env['lhdn.malaysia.state.code'].search([]).unlink()
        response = requests.get(self.malaysian_states_code_url)
        if response.status_code == 200:
            response_dict = response.json()
            msic_code_dict = []
            for rec in response_dict:
                msic_code_dict.append({'name': rec.get('Description'), 'code': rec.get('Code')})
            if msic_code_dict:
                self.env['lhdn.item.classification.code'].sudo().create(msic_code_dict)
        else:
            raise UserError(_(response))

    def cron_create_invoice_usings_sftp(self):
        lhdn_setup_id = self.env['lhdn.setup'].search([], limit=1)
        if lhdn_setup_id.create_invoice_using_sftp_server:
            host = lhdn_setup_id.sftp_server_ip
            username = lhdn_setup_id.sftp_server_user
            password = lhdn_setup_id.sftp_server_passwords
            tin = self.env.company.partner_id.tin.lower()
            # remote_dir = f"/home/ubuntu/ftp_operation/c4874711040/output"
            remote_dir = f"/home/ubuntu/ftp_operation/{tin}/output2"
            try:
                # Create an SFTP client
                transport = paramiko.Transport((host, 22))
                transport.connect(username=username, password=password)
                sftp = paramiko.SFTPClient.from_transport(transport)
                # List all JSON files in the remote directory
                total_files = len(sftp.listdir(remote_dir))
                total_created_new_moves_in_odoo =[]
                not_createds_moveas_ins_odoo = []
                for count,filename in enumerate(sftp.listdir(remote_dir),start=1):
                    if filename.endswith(".json"):  # Only process JSON files
                        remote_file_path = f"{remote_dir}/{filename}"
                        # Open the file directly on the server
                        with sftp.file(remote_file_path, "r") as remote_file:
                            file_content = remote_file.read().decode("utf-8")  # Read and decode the file content
                            move = json.loads(file_content)  # Parse JSON data
                            # move = {}
                            # Example: Extracting fields (adjust based on your JSON structure)
                            odoo_move_type = SFTP_AI_DOCUMENTS_TYPE_CODE[move.get('document_type')]
                            odoo_move_id_found = self.env['account.move'].sudo().search(
                                [('portal_ai_inv_number', '=', move.get('invoice_number'))])
                            if not odoo_move_id_found:
                                external_partner_obj = move.get('partner_id')
                                partner_domain = []
                                tin = external_partner_obj.get('tax_identification_number')
                                brn = external_partner_obj.get('business_registration_number')
                                name = external_partner_obj.get('name')

                                if name:
                                    partner_domain.append(('name', 'ilike',name))
                                if tin:
                                    partner_domain = expression.OR([[('tin', '=',tin)], partner_domain])
                                if brn:
                                    partner_domain = expression.OR([[('brn', '=',brn)], partner_domain])
                                odoo_partner_id = self.env['res.partner'].sudo().search(partner_domain,limit=1)
                                if not odoo_partner_id:
                                    odoo_state_id = self.env['res.country.state'].sudo().search(
                                        ['|', ('name', 'ilike', external_partner_obj.get('state')),
                                         ('code', '=',external_partner_obj.get('state'))], limit=1)
                                    # if not odoo_state_id:
                                    #     error.append({'external_system_id': move.get('external_system_db_id'),
                                    #                   'error_str': "partner ->State not found ins API server"})
                                    #     return [], [], error

                                    odoo_country_id = self.env['res.country'].sudo().search(
                                        [('code', '=', external_partner_obj.get('country_code'))], limit=1)
                                    # if not odoo_country_id:
                                    #     error.append({'external_system_id': move.get('external_system_db_id'),
                                    #                   'error_str': "partner ->Country not found ins API server"})
                                    #     return [], [], error

                                    odoo_msic_code_id = self.env['lhdn.msic.code'].sudo().search(
                                        [('code', '=', external_partner_obj.get('msic_code'))], limit=1)
                                    # if not odoo_msic_code_id:
                                    #     error.append({'external_system_id': move.get('external_system_db_id'),
                                    #                   'error_str': "partner ->MSIC Code not found ins API server"})
                                    #     return [], [], error

                                    odoo_partner_id = self.env['res.partner'].sudo().create({
                                        'name': external_partner_obj.get('name'),
                                        # 'external_system_db_id': external_partner_obj.get('external_system_db_id'),
                                        'brn': external_partner_obj.get('business_registration_number'),
                                        'msic_code_id': odoo_msic_code_id.id,
                                        'tin': external_partner_obj.get('tax_identification_number'),
                                        'street': external_partner_obj.get('street'),
                                        'city': external_partner_obj.get('city'),
                                        'zip': external_partner_obj.get('postal_code'),
                                        'state_id': odoo_state_id.id,
                                        'country_id': odoo_country_id.id,
                                        'tin_status': 'validated'
                                    })

                                move_dict = {
                                    'portal_ai_inv_number':move.get('invoice_number'),
                                    # 'external_system_invoice_number': move.get('external_system_invoice_number') or False,
                                    'partner_id': odoo_partner_id.id,
                                    'move_type':odoo_move_type,
                                    'invoice_date': move.get('invoice_date') if move.get('invoice_date') else False
                                }

                                external_currency_id = move.get('currency_id')
                                odoo_currency_id_found = False
                                if external_currency_id:
                                    odoo_currency_id_found = self.env['res.currency'].sudo().search(
                                        ['|', ('name', '=', external_currency_id),
                                         ('full_name', '=', external_currency_id)], limit=1)
                                if odoo_currency_id_found:
                                    move_dict.update({'currency_id': odoo_currency_id_found.id})

                                # if origin_uuid:
                                #     move_dict.update({'origin_lhdn_uuid': origin_uuid})
                                lines = []
                                for external_move_line in move.get('move_line'):
                                    external_products_obj = external_move_line.get('product_id')

                                    odoo_products_classification_id = self.env[
                                        'lhdn.item.classification.code'].sudo().search(
                                        [('code', '=', external_products_obj.get('classification_code'))], limit=1)
                                    # if not odoo_products_classification_id:
                                    #     error.append({'external_system_id': move.get('external_system_db_id'),
                                    #                   'error_str': f"Move Lines ->{external_products_obj.get('name')} -> classification_code not found ins API server"})
                                    #     return [], [], error

                                    odoo_product_id = self.env['product.product'].sudo().search(
                                        [('name', 'ilike',
                                          external_products_obj.get('name'))],limit=1)
                                    if not odoo_product_id:
                                        odoo_product_id = self.env['product.product'].sudo().create({
                                            'name': external_products_obj.get('name'),
                                            # 'external_system_db_id': external_products_obj.get('external_system_db_id'),
                                            'lhdn_classification_id': odoo_products_classification_id.id
                                        })
                                    lines.append((0, 0, {
                                        "product_id": odoo_product_id.id,
                                        "display_type": 'product',
                                        "account_id": 33,
                                        "quantity": external_move_line.get('quantity'),
                                        "price_unit": external_move_line.get('price_unit'),
                                    }))
                                move_dict.update({'line_ids': lines})
                                new_move_id = False
                                try:
                                    new_move_id = self.env['account.move'].sudo().create(move_dict)
                                    total_created_new_moves_in_odoo.append(filename)
                                except Exception as e:
                                    not_createds_moveas_ins_odoo.append({filename:e})
                                _logger.info(f"processed file ==>{filename}==>{move.get('document_type')}, {count} out of {total_files}")
                                # new_create_odoo_move_list.append(new_orders_id.id)
                            else:
                                not_createds_moveas_ins_odoo.append(filename)
                _logger.info(f"--------------------SFTP Invocies Creatings ins odoo----------------------")
                _logger.info(f"New Created ==>{total_created_new_moves_in_odoo}")
                _logger.info(f"Not Created ==>{not_createds_moveas_ins_odoo}")
            except Exception as e:
                print(f"Failed to connect or perform SFTP operations: {e}")
