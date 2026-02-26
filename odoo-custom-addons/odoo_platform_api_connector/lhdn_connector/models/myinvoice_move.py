from odoo import api, fields, models
import requests
from datetime import datetime, timedelta, timezone
import json


class MyInvocieMove(models.Model):
    _name = 'myinvoice.move'
    _inherit = 'mail.thread'
    _description = 'MyInvoiceMove'
    _rec_name = 'uuid'

    uuid = fields.Char(string="UUID")
    submissionUID = fields.Char(string="Submission UID")
    longId = fields.Char(string="Long Id")
    internalId = fields.Char(string="Internal Id")
    typeName = fields.Char(string="Type Name")
    typeVersionName = fields.Char(string="Type Version Name")
    issuerTin = fields.Char(string="Issuer Tin")
    issuerName = fields.Char(string="Issuer Name")
    receiverTin = fields.Char(string="Receiver Id")
    receiverName = fields.Char(string="Receiver Name")
    dateTimeIssued = fields.Datetime(string="DateTime Issued", help="The date and time when the document was issued.")
    dateTimeReceived = fields.Datetime(string="DateTime Received",
                                       help="The date and time when the document was submitted.")
    dateTimeValidated = fields.Datetime(string="DateTime Validated",
                                        help="The date and time when the document passed all validations and moved to the valid state.")
    totalSales = fields.Float(string="Total Sales", help="Total sales amount of the document in MYR.")
    totalDiscount = fields.Float(string="Total Discount", help="Total discount amount of the document in MYR.")
    netAmount = fields.Float(string="Net Amount", help="Total net amount of the document in MYR.")
    total = fields.Float(string="Total", help="Total amount of the document in MYR.")
    status = fields.Char(string="Status")
    cancelDateTime = fields.Datetime(string="Cancel DateTime",
                                     help="Refer to the document cancellation that has been initiated by the taxpayer “issuer” of the document on the system, will be in UTC format")
    rejectRequestDateTime = fields.Datetime(string="RejectRequest DateTime",
                                            help="Refer to the document rejection request that has been initiated by the taxpayer “receiver” of the document on the system, will be in UTC format")
    documentStatusReason = fields.Char(string="Document Status Reason",
                                       help="Mandatory: Reason of the cancellation or rejection of the document.")
    createdByUserId = fields.Char(string="Created By UserId",
                                  help="User created the document. Can be ERP ID or User Email")
    supplierTIN = fields.Char(string="Supplier TIN", help="TIN of issuer")
    supplierName = fields.Char(string="Supplier Name")
    submissionChannel = fields.Char(string="Submission Channel",
                                    help="Channel through which document was introduced into the system")
    intermediaryName = fields.Char(string="Intermediary Name", help="Intermediary company name")
    intermediaryTIN = fields.Char(string="intermediary TIN")
    buyerName = fields.Char(string="Buyer Name")
    buyerTIN = fields.Char(string="Buyer TIN")
    active = fields.Boolean(string="Active", default=True)

    def lhdn_token_generation(self):
        lhdn_base_url = self.env.company.lhdn_api_url
        # Froms the AccountingSupplierParty
        # onbehalfof_tin = onbehalfof_tin
        headers = {
            # 'grant_type': 'client_credentials', 'scope': 'InvoicingAPI',
            'Content-Type': 'application/x-www-form-urlencoded',
            # 'onbehalfof': onbehalfof_tin
        }
        payload = {'client_id': self.env.company.lhdn_api_client_id,
                   'client_secret': self.env.company.lhdn_api_client_password,
                   'grant_type': 'client_credentials',
                   'scope': 'InvoicingAPI',
                   }
        res = requests.post(lhdn_base_url + '/connect/token', data=payload,
                            headers=headers)
        return res.json()

    def parse_datetime(self, date_string):
        # Check if the string contains fractional seconds (i.e., a '.' before 'Z')
        date = date_string.split('T')[0]
        time = date_string.split('T')[1]
        if '.' in time:
            time = time.split('.')[0]
        else:
            time = time.split('Z')[0]
        date_string = date + 'T' + time
        # if '.' in date_string:
        #     try:
        #     # Trim to 6 digits for microseconds and parse
        #         return datetime.strptime(date_string[:26], '%Y-%m-%dT%H:%M:%S.%f').replace(microsecond=0)
        #     except Exception as e:
        #         print("Hiieas")
        # else:
        # Parse the string without microseconds
        try:
            return datetime.strptime(date_string, '%Y-%m-%dT%H:%M:%S')
        except Exception as e:
            print("Hiieas")

    def get_recent_documents_from_lhdn(self):
        # lhdn_base_url = self.env.company.lhdn_api_url
        # generated_token = self.lhdn_token_generation()
        # if generated_token.get('access_token'):
        # access_token = generated_token.get('access_token')
        # headers = {'Content-Type': 'application/json',
        #            'Authorization': f'Bearer {access_token}'}
        lhdn_setup_id = self.env['lhdn.setup'].search([], limit=1)
        # if lhdn_setup_id.choose_submission_way == 'intermediate_api':
        headers = {'Content-Type': 'application/json'}
        data = {
            'client_id': lhdn_setup_id.peppol_sync_api_client_id,
            'client_password': lhdn_setup_id.peppol_sync_api_client_password,
            'tin': self.env.company.partner_id.tin
            # 'api_use': "myinvoice_api",
            # 'issuer_tin': issuer_tin,
            # 'uuid': self.lhdn_uuid,
            # 'cancel_reason': self.lhdn_document_cancellation_reason
            # 'peppol_credential': {},
            # 'myinvoice_credential': {'client_id': lhdn_setup_id.lhdn_api_client_id,
            #                          'client_secret': lhdn_setup_id.lhdn_api_client_password},
            # "invoice_dict": {'inv_number': self.name, 'cancel_reason': self.lhdn_document_cancellation_reason},
            # 'onbehalfof_tin': self.company_id.partner_id.tin
        }
        # This is only for the single documents submission
        payload = {}
        # current_time = datetime.now(timezone.utc)
        # past_time = current_time - timedelta(days=31)
        # formatted_from_time = past_time.strftime("%Y-%m-%d")
        # query = f"submissionDateFrom={formatted_from_time}&submissionDateTo={datetime.now(timezone.utc).strftime('%Y-%m-%d')}&pageSize=50"
        # res = requests.get(lhdn_base_url + '/api/v1.0/documents/recent?' + query, data=payload,
        #                    headers=headers)
        res = requests.post(f"{lhdn_setup_id.peppol_sync_api_base_url}/v1/get_recent_documents",
                            params=json.dumps(data),
                            headers=headers)
        if res.status_code == 200:
            res = res.json()
            inv_list = res.get('lhdn_recents_documents_list')
            # total_pages = res.get('metadata').get('totalPages')
            myinvoice_move_obj = self.env['myinvoice.move'].sudo()
            myinvoice_move_list = []
            myinvoice_move_created_ids = myinvoice_move_obj.search([]).mapped('uuid')
            for inv in inv_list:
                if inv.get('uuid') not in myinvoice_move_created_ids:
                    dateTimeIssued_formatted = self.parse_datetime(inv.get('dateTimeIssued')) if inv.get(
                        'dateTimeIssued') else False

                    dateTimeReceived_formatted = self.parse_datetime(inv.get('dateTimeReceived')) if inv.get(
                        'dateTimeReceived') else False

                    dateTimeValidated_formatted = self.parse_datetime(inv.get('dateTimeValidated')) if inv.get(
                        'dateTimeValidated') else False

                    cancelDateTime_formatted = self.parse_datetime(inv.get('cancelDateTime')) if inv.get(
                        'cancelDateTime') else False

                    rejectRequestDateTime_formatted = self.parse_datetime(
                        inv.get('rejectRequestDateTime')) if inv.get('rejectRequestDateTime') else False

                    myinvoice_move_list.append({
                        'uuid': inv.get('uuid'),
                        'submissionUID': inv.get('submissionUid'),
                        'longId': inv.get('longId'),
                        'internalId': inv.get('internalId'),
                        'typeName': inv.get('typeName'),
                        'typeVersionName': inv.get('typeVersionName'),
                        'issuerTin': inv.get('issuerTIN'),
                        'issuerName': inv.get('issuerName'),
                        'receiverTin': inv.get('receiverTIN'),
                        'receiverName': inv.get('receiverName'),
                        'dateTimeIssued': dateTimeIssued_formatted,
                        'dateTimeReceived': dateTimeReceived_formatted,
                        'dateTimeValidated': dateTimeValidated_formatted,
                        'totalSales': inv.get('totalSales'),
                        'totalDiscount': inv.get('totalDiscount'),
                        'netAmount': inv.get('netAmount'),
                        'total': inv.get('total'),
                        'status': inv.get('status'),
                        'cancelDateTime': cancelDateTime_formatted,
                        'rejectRequestDateTime': rejectRequestDateTime_formatted,
                        'documentStatusReason': inv.get('documentStatusReason'),
                        'createdByUserId': inv.get('createdByUserId'),
                        'supplierTIN': inv.get('supplierTIN'),
                        'supplierName': inv.get('supplierName'),
                        'submissionChannel': inv.get('submissionChannel'),
                        'intermediaryName': inv.get('intermediaryName'),
                        'intermediaryTIN': inv.get('intermediaryTIN'),
                        'buyerName': inv.get('buyerName'),
                        'buyerTIN': inv.get('buyerTIN')
                    })
            if myinvoice_move_list:
                myinvoice_move_obj.create(myinvoice_move_list)

            # for page in range(2, total_pages + 1):
            #     myinvoice_move_created_ids = myinvoice_move_obj.search([]).mapped('uuid')
            #     query = query + f"&pageNo={page}&pageSize=50"
            #     res = requests.get(lhdn_base_url + '/api/v1.0/documents/recent?' + query, data=payload,
            #                        headers=headers)
            #     if res.status_code == 200:
            #         res = res.json()
            #         inv_list = res.get('result')
            #         # total_pages = res.get('metadata').get('totalPages')
            #         myinvoice_move_obj = self.env['myinvoice.move'].sudo()
            #         myinvoice_move_list = []
            #         for inv in inv_list:
            #             if inv.get('uuid') not in myinvoice_move_created_ids:
            #                 dateTimeIssued_formatted = self.parse_datetime(inv.get('dateTimeIssued')) if inv.get(
            #                     'dateTimeIssued') else False
            #
            #                 dateTimeReceived_formatted = self.parse_datetime(
            #                     inv.get('dateTimeReceived')) if inv.get(
            #                     'dateTimeReceived') else False
            #
            #                 dateTimeValidated_formatted = self.parse_datetime(
            #                     inv.get('dateTimeValidated')) if inv.get(
            #                     'dateTimeValidated') else False
            #
            #                 cancelDateTime_formatted = self.parse_datetime(inv.get('cancelDateTime')) if inv.get(
            #                     'cancelDateTime') else False
            #
            #                 rejectRequestDateTime_formatted = self.parse_datetime(
            #                     inv.get('rejectRequestDateTime')) if inv.get('rejectRequestDateTime') else False
            #
            #                 myinvoice_move_list.append({
            #                     'uuid': inv.get('uuid'),
            #                     'submissionUID': inv.get('submissionUid'),
            #                     'longId': inv.get('longId'),
            #                     'internalId': inv.get('internalId'),
            #                     'typeName': inv.get('typeName'),
            #                     'typeVersionName': inv.get('typeVersionName'),
            #                     'issuerTin': inv.get('issuerTIN'),
            #                     'issuerName': inv.get('issuerName'),
            #                     'receiverTin': inv.get('receiverTIN'),
            #                     'receiverName': inv.get('receiverName'),
            #                     'dateTimeIssued': dateTimeIssued_formatted,
            #                     'dateTimeReceived': dateTimeReceived_formatted,
            #                     'dateTimeValidated': dateTimeValidated_formatted,
            #                     'totalSales': inv.get('totalSales'),
            #                     'totalDiscount': inv.get('totalDiscount'),
            #                     'netAmount': inv.get('netAmount'),
            #                     'total': inv.get('total'),
            #                     'status': inv.get('status'),
            #                     'cancelDateTime': cancelDateTime_formatted,
            #                     'rejectRequestDateTime': rejectRequestDateTime_formatted,
            #                     'documentStatusReason': inv.get('documentStatusReason'),
            #                     'createdByUserId': inv.get('createdByUserId'),
            #                     'supplierTIN': inv.get('supplierTIN'),
            #                     'supplierName': inv.get('supplierName'),
            #                     'submissionChannel': inv.get('submissionChannel'),
            #                     'intermediaryName': inv.get('intermediaryName'),
            #                     'intermediaryTIN': inv.get('intermediaryTIN'),
            #                     'buyerName': inv.get('buyerName'),
            #                     'buyerTIN': inv.get('buyerTIN')
            #                 })
            #         if myinvoice_move_list:
            #             myinvoice_move_obj.create(myinvoice_move_list)
