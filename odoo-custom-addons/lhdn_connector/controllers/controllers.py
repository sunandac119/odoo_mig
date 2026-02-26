# -*- coding: utf-8 -*-
from odoo import http, _
from odoo.http import request
import requests
import logging
import json

_logger = logging.getLogger("Documetns datas ==>")
from datetime import datetime, timedelta
from odoo.addons.portal.controllers.portal import CustomerPortal
import json
import os
import base64
import logging

_logger = logging.getLogger("LHDN")


# from odoo.http import request
# import json


class PortalAccount(CustomerPortal):

    @http.route(['/my/e_invoice_upload'], type='http', auth="user", website=True)
    def portal_my_stock_transfer(self, page=1, date_begin=None, date_end=None, sortby=None, filterby=None, **kw):
        # values = self._prepare_my_invoices_values(page, date_begin, date_end, sortby, filterby)
        #
        # # pager
        # pager = portal_pager(**values['pager'])
        #
        # # content according to pager and archive selected
        # invoices = values['invoices'](pager['offset'])
        # request.session['my_invoices_history'] = invoices.ids[:100]
        #
        # values.update({
        #     'invoices': invoices,
        #     'pager': pager,
        # })
        # portal_inv_store_path = '/Users/onlymac/workspace/odoo_v17/custom_addons/portal_inv'
        portal_inv_store_path = '/home/ubuntu/portal_inv'
        todays_inv_path = portal_inv_store_path + '/' + datetime.now().date().strftime("%d_%m_%Y")
        todays_not_completed_dir_path = todays_inv_path + '/' + 'not_completed'

        total_remainings_files = 0
        if os.path.exists(todays_not_completed_dir_path):
            total_remainings_files = len(os.listdir(todays_not_completed_dir_path))

        invoices = request.env['account.move'].sudo().search(
            [('is_created_from_ai', '=', True)])
        # ('company_id', '=', request.env.company.id)
        values = {}
        values.update({
            'invoices': invoices,
            'remains_to_process': total_remainings_files,
            # 'pager': pager,
        })
        return request.render("lhdn_connector.portal_e_invoice_upload", values)

    @http.route(['/my/credit_managements'], type='http', auth="user", website=True)
    def portal_my_credit_managements(self, **kw):
        # values = self._prepare_my_invoices_values(page, date_begin, date_end, sortby, filterby)
        #
        values = {}
        lhdn_setup_id = request.env['lhdn.setup'].search([], limit=1)
        # lhdn_base_url = lhdn_setup_id.lhdn_sandbox_base_url if lhdn_setup_id.lhdn_connection_server_type == 'sandbox' else lhdn_setup_id.lhdn_production_base_url
        com_tin = request.env.company.partner_id.tin
        if lhdn_setup_id.choose_submission_way == 'intermediate_api':
            headers = {'Content-Type': 'application/json'}
            start_date = datetime.now().date() - timedelta(days=90)
            data = {
                'client_id': lhdn_setup_id.peppol_sync_api_client_id,
                'client_password': lhdn_setup_id.peppol_sync_api_client_password,
                "tin": com_tin,
                "startDate": start_date.strftime("%Y-%m-%d") + "T00:00:00",
                "endDate": datetime.now().date().strftime("%Y-%m-%d") + "T23:59:59"
            }
            values.update({
                'start_date': start_date.strftime("%Y-%m-%d") + "T00:00:00",
                'end_date': datetime.now().date().strftime("%Y-%m-%d") + "T23:59:59"})
            res = requests.post(f"{lhdn_setup_id.peppol_sync_api_base_url}/v1/fetch_credit_info",
                                params=json.dumps(data),
                                headers=headers)
            if res.status_code == 200:
                res = res.json()
                credit_usage_list = res.get('creditUsage')
                credit_usage_list_sorted = []
                total_usages = 0.0
                if credit_usage_list:
                    credit_usage_list_sorted = sorted(credit_usage_list, key=lambda x: datetime.fromisoformat(
                        x['createdAt'].split('.')[0]), reverse=True)
                    total_usages = sum(item['usage'] for item in credit_usage_list_sorted)
                values.update({
                    'company_name': request.env.company.name,
                    'tin': com_tin,
                    # 'remainingCredit': res.get('remainingCredit'),
                    'credit_usage_list': credit_usage_list_sorted,
                    'total_usages': total_usages,
                })
            else:
                error_return_dict = res.json()
                if error_return_dict.get('error'):
                    values.update({
                        'error': error_return_dict.get('error')
                    })
                else:
                    values.update({
                        'error': "Gettings ans error durings fetching ans informations about your credit informations"
                    })
        return request.render("lhdn_connector.portal_my_credit_managements", values)

    @http.route(['/my/invoices_templates'], type='http', auth="user", website=True)
    def portal_my_invoice_templates(self, **kw):
        # values = self._prepare_my_invoices_values(page, date_begin, date_end, sortby, filterby)
        #
        values = {}
        # values.update({
        #     'invoices': invoices,
        #     'remains_to_process':total_remainings_files,
        #     # 'pager': pager,
        # })
        return request.render("lhdn_connector.portal_my_invoice_templates", values)

    def _get_mandatory_fields(self):
        """ This method is there so that we can override the mandatory fields """
        res = super()._get_mandatory_fields()
        res.extend(['company_name', 'company_start_date', 'is_vendor_or_customer', 'tin', 'sst', 'brn', 'msic_code_id',
                    'mobile', 'zipcode', 'state_id'])
        return res

    def _get_optional_fields(self):
        """ This method is there so that we can override the optional fields """
        res = super()._get_optional_fields()
        res = ['vat', 'old_brn', 'sst_group', 'tourism_tax_no', 'street2']
        return res

    def on_account_update(self, values, partner):
        res = super().on_account_update(values, partner)
        if values.get('msic_code_id'):
            values.update({'msic_code_id': int(values.get('msic_code_id'))})
        return res


class LhdnConnector(http.Controller):

    @http.route('/v1/receive/peppol_docs', type='http', auth='public', methods=['POST'], csrf=False)
    def get_my_peppol_documents(self, **kw):
        kw = json.loads(list(kw.keys())[0])
        _logger.info(f"Documents data gettings ins Ap Addons ==> {kw}")

        invoice_type = 'in_invoice' if kw.get('document_type') == "Invoice" else 'in_refund'
        currency_code = kw.get('currency_code')
        odoo_currency_code = request.env['res.currency'].sudo().search([('name', 'ilike', currency_code)], limit=1)
        invoice_date = kw.get('invoice_date')
        receiver_peppol_id = kw.get('receiver_peppol_id')
        sender_peppol_id = kw.get('sender_peppol_id')
        invoice_lines = kw.get('invoices_lines')
        peppol_inv_ref = kw.get('peppol_inv_ref')

        vendor_id = request.env['res.partner'].sudo().search([('peppol_id', '=', sender_peppol_id)], limit=1)

        documents_dict = {
            'partner_id': vendor_id.id if vendor_id else False,
            'move_type': invoice_type,
            # 'is_created_from_peppol_received_docs': True,
            # 'peppol_received_docs_ref': peppol_inv_ref,
            'currency_id': odoo_currency_code.id if odoo_currency_code else False,
            'invoice_date': invoice_date
        }
        documents_id = request.env['account.move'].sudo().create(documents_dict)

        for line in invoice_lines:
            tax = line.get('Percent')
            purchase_tax = False
            if tax:
                purchase_tax = request.env['account.tax'].sudo().search(
                    [('amount', '=', tax), ('type_tax_use', '=', 'purchase')], limit=1)
            documents_id.invoice_line_ids = [(0, 0, {
                'name': line.get('description'),
                'quantity': line.get('InvoicedQuantity'),
                'price_unit': line.get('PriceAmount'),
                'tax_ids': [(6, 0, purchase_tax.ids)] if purchase_tax else False,
            })]

        documents_id.message_post(
            body=_("This Documents We Received from the Peppol Network and we created", description=123))
        documents_id.peppol_received_docs_ref = peppol_inv_ref
        documents_id.is_created_from_peppol_received_docs = True

    @http.route('/post_e_invoice_files', type='http', auth='public', methods=['POST'], csrf=False)
    def upload_files(self, **kwargs):
        files = request.httprequest.files.getlist('files')

        # portal_inv_store_path = '/Users/onlymac/workspace/odoo_v17/custom_addons/portal_inv'
        portal_inv_store_path = '/home/ubuntu/portal_inv'
        todays_inv_path = portal_inv_store_path + '/' + datetime.now().date().strftime("%d_%m_%Y")
        todays_completed_dir_path = todays_inv_path + '/' + 'completed'
        todays_not_completed_dir_path = todays_inv_path + '/' + 'not_completed'

        # Check if the directory exists
        if not os.path.exists(portal_inv_store_path):
            # Create the directory
            os.makedirs(portal_inv_store_path, mode=0o755, exist_ok=True)
        if not os.path.exists(todays_inv_path):
            os.makedirs(todays_inv_path, mode=0o755, exist_ok=True)

        if not os.path.exists(todays_completed_dir_path):
            os.makedirs(todays_completed_dir_path, mode=0o755, exist_ok=True)

        if not os.path.exists(todays_not_completed_dir_path):
            os.makedirs(todays_not_completed_dir_path, mode=0o755, exist_ok=True)

        if os.path.exists(todays_not_completed_dir_path):
            for file in files:
                if file.filename.endswith('.pdf'):
                    filename = file.filename
                    filepath = os.path.join(todays_not_completed_dir_path, filename)
                    # file.save(filepath)
                    with open(filepath, 'wb') as f:
                        f.write(file.read())

        if not files:
            return "No files uploaded", 400

        return request.redirect('/my/e_invoice_upload')

    def send_to_analyze_invoice(self, file):
        url = 'http://103.76.88.17:5000/analyze_invoice'
        files = [('file', (file.filename, file.stream, file.content_type))]
        response = False
        try:
            response = requests.post(url, files=files, timeout=40)
        except Exception as e:
            _logger.info(f"Errors gettings durings ans endpoints dataeas gettingyieas ==> {e}")
        # time.sleep(10)
        return response

    @http.route('/account_move/get_lhdn_documents_status', type='json', auth='user', methods=['POST'], csrf=False)
    def call_invoice_method(self, invoice_id):
        try:
            invoice = request.env['account.move'].sudo().browse(int(invoice_id))
            if not invoice:
                return {'success': False, 'message': 'Invoice not found'}

            # Call your desired method here
            invoice.get_lhdn_documents_status()

            return {'success': True, 'message': 'Method called successfully'}
        except Exception as e:
            return {'success': False, 'message': str(e)}

    @http.route('/account_move/manually_documents_send_in_peppol_network', type='json', auth='user', methods=['POST'],
                csrf=False)
    def call_peppol_methods_method(self, invoice_id):
        try:
            invoice = request.env['account.move'].sudo().browse(int(invoice_id))
            if not invoice:
                return {'success': False, 'message': 'Invoice not found'}

            # Call your desired method here
            invoice.manually_documents_send_in_peppol_network()

            return {'success': True, 'message': 'Method called successfully'}
        except Exception as e:
            return {'success': False, 'message': str(e)}

    @http.route('/post_invoice_templates_fileas', type='http', auth='public', methods=['POST'], csrf=False)
    def post_invoice_templates_fileas(self, **kwargs):
        # Retrieve the uploaded file
        uploaded_file = request.httprequest.files.get('files')

        # Check if the file is present
        if uploaded_file:
            # Get the filename
            filename = uploaded_file.filename

            # Read the content of the file
            file_content = uploaded_file.read()

            # Encode the file content to base64 for display in the frontend
            encoded_file = base64.b64encode(file_content).decode('utf-8')

            # Create a URL for the PDF (you might want to change this according to your needs)
            pdf_url = f"{encoded_file}"

            # Render the response directly with the PDF URL
            return request.redirect('/my/invoices_templates?pdf_url=%s' % (pdf_url))

        return request.redirect('/my/invoices_templates')  # Redirect in case of no file uploaded
