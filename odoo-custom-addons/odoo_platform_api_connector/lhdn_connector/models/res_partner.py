from odoo import api, fields, models, _
from odoo.exceptions import MissingError, ValidationError, AccessError, UserError
import requests
import json


class ResPartner(models.Model):
    _inherit = 'res.partner'

    tin = fields.Char("TIN", copy=False)
    brn = fields.Char("BRN", copy=False)
    sst = fields.Char("SST", copy=False)
    email_e_invoice = fields.Char("Email (e-Invoice Notification)", copy=False)
    contact_e_invoice = fields.Char("Contact (e-Invoice Notification)", copy=False)
    whatsapp_number_e_invoice = fields.Char("WhatsApp Number (e-Invoice Notification)", copy=False)
    msic_code_id = fields.Many2one('lhdn.msic.code', string="MSIC Code", copy=False)
    tin_status = fields.Selection([('validated', 'Validated'), ('invalid', 'Invalid')], string="TIN Status",
                                  default='invalid', copy=False)
    special_identifier = fields.Selection([
        ('01', 'SSM Number'),
        ('02', 'Sabah'),
        ('03', 'Sarawak'),
        ('04', 'Foreign Businesses'),
        ('05', 'Testing Purpose')], string="Special Identifier", default='01', copy=False)

    peppol_id = fields.Char(string="Peppol Id", copy=False)
    peppol_status = fields.Selection([
        ('not_registered', 'Not Registered'),
        ('registered', 'Registered'),
        ('need_to_kyc', 'Need to Do KYC Process')], string="Peppol Registration Status", default='not_registered',
        copy=False)
    send_documents_via_peppol = fields.Boolean(string="Automatically Send Documents via Peppol?")
    peppol_lookup_id = fields.Char(string="Peppol SML Lookup")
    peppol_sml_pdf_signed = fields.Binary(string="Peppol SML PDF Signed", attachment=True)

    company_start_date = fields.Date(string="Start Date of your company")
    is_vendor_or_customer = fields.Selection(selection=[('customer','Customer'),('vendor','Vendor')],string="Are you an Vendor or Customer?")
    old_brn = fields.Char(string="Old BRN")
    sst_group = fields.Char(string="SST Group")
    tourism_tax_no = fields.Char(string="Tourism Tax No")


    @api.onchange('send_documents_via_peppol')
    def send_documents_via_peppol_onchange_method(self):
        if self.send_documents_via_peppol and self.peppol_status != "registered":
            raise UserError(
                _("First of all you need to register in the Peppol SML by clicking the Register in Peppol SML Buttons"))

    def validatings_tin_number(self):
        if not self.tin:
            raise UserError(_("Please Fill Ups the TIN"))
        if not self.brn:
            raise UserError(_("Please Fill Ups the BRN"))
        lhdn_setup_id = self.env['lhdn.setup'].search([], limit=1)
        # lhdn_base_url = lhdn_setup_id.lhdn_sandbox_base_url if lhdn_setup_id.lhdn_connection_server_type == 'sandbox' else lhdn_setup_id.lhdn_production_base_url
        # generated_token = self.env['account.move'].lhdn_token_generation(lhdn_setup_id.lhdn_api_client_id,
        #                                                                  lhdn_setup_id.lhdn_api_client_password,
        #                                                                  lhdn_setup_id)

        headers = {'Content-Type': 'application/json'}
        data = {
            'client_id': lhdn_setup_id.peppol_sync_api_client_id,
            'client_password': lhdn_setup_id.peppol_sync_api_client_password,
            'tin':self.tin,
            'brn':self.brn
        }
        res = requests.post(f"{lhdn_setup_id.peppol_sync_api_base_url}/v1/tin_brn_validations", params=json.dumps(data),
                            headers=headers)

        if res.status_code == 200:
            res = res.json()
            if res.get('validated'):
                self.tin_status = 'validated'
            else:
                self.tin_status = 'invalid'
        else:
            self.tin_status = 'invalid'

    @api.model
    def create(self, vals):
        res = super(ResPartner, self).create(vals)
        peppol_id = f"0230:{res.special_identifier}{res.brn}"
        res['peppol_id'] = peppol_id
        return res

    def write(self, vals):
        # Need to checks privisolus brn is registeds withs ans peppol then restrict to cahnges the brn
        if vals.get('brn') and vals.get('special_identifier'):
            vals['peppol_id'] = f"0230:{vals['special_identifier']}{vals['brn']}"
        else:
            if vals.get('brn'):
                vals['peppol_id'] = f"0230:{self.special_identifier}{vals['brn']}"
            if vals.get('special_identifier'):
                vals['peppol_id'] = f"0230:{vals['special_identifier']}{self.brn}"
        return super(ResPartner, self).write(vals)

    def register_peppol_participants(self):
        lhdn_setup_id = self.env['lhdn.setup'].search([], limit=1)
        if not self.peppol_id:
            raise UserError(_("Fill up thes Peppol ID Fields data"))

        peppol_participants_data_dict = {
            'api_client_id': lhdn_setup_id.peppol_sync_api_client_id,
            'api_client_password': lhdn_setup_id.peppol_sync_api_client_password,
            'participants_state': self.state_id.name,
            'peppol_participants_name': self.name,
            'peppol_id': self.peppol_id.split(':')[1]
        }

        if not self.state_id:
            raise UserError(_("Fill up the State Name"))
        if not self.peppol_id:
            raise UserError(_("Needs to an generate the Peppol ID First"))
        headers = {'Content-Type': 'application/json'}
        res = requests.post(f"{lhdn_setup_id.peppol_sync_api_base_url}/v1/register/peppol_participants",
                            params=json.dumps(peppol_participants_data_dict),
                            headers=headers)

        if res.status_code == 201:
            self.peppol_status = 'registered'
        elif res.status_code == 202:
            self.peppol_status = 'need_to_kyc'
        elif res.status_code == 409:
            # Companyieas alreadys registerings withs ans anothers organizationyieas
            self.peppol_status = 'registered'
        else:
            self.peppol_status = 'not_registered'
            raise UserError(f"Error Ocuurings ==>{res.text}")

    def peppol_kyc_needs_complete(self):
        return True

    def peppol_id_sml_lookup(self):
        if not self.peppol_lookup_id:
            raise UserError(("Filled Up the  Peppol Lookup Ids fields data"))
        lhdn_setup_id = self.env['lhdn.setup'].search([], limit=1)
        peppol_lookup_dict = {
            'api_client_id': lhdn_setup_id.peppol_sync_api_client_id,
            'api_client_password': lhdn_setup_id.peppol_sync_api_client_password,
            'peppol_lookup_id': self.peppol_lookup_id
        }
        headers = {'Content-Type': 'application/json'}
        res = requests.post(f"{lhdn_setup_id.peppol_sync_api_base_url}/v1/lookup/peppol_participants",
                            params=json.dumps(peppol_lookup_dict),
                            headers=headers)

        if res.status_code == 200:
            raise UserError((f"Peppol Id {self.peppol_lookup_id} is present in SML"))
        elif res.status_code == 404:
            raise UserError((f"Peppol Id {self.peppol_lookup_id} is not found in SML"))
        else:
            raise UserError((f"Geetings some error while performing this operations ==> {res.text}"))

    def peppol_id_global_lookup(self):
        if not self.peppol_lookup_id:
            raise UserError(("Filled Up the  Peppol Lookup Ids fields data"))
        lhdn_setup_id = self.env['lhdn.setup'].search([], limit=1)
        peppol_lookup_dict = {
            'api_client_id': lhdn_setup_id.peppol_sync_api_client_id,
            'api_client_password': lhdn_setup_id.peppol_sync_api_client_password,
            'peppol_lookup_id': self.peppol_lookup_id,
            'is_global_lookup': True
        }
        headers = {'Content-Type': 'application/json'}
        res = requests.post(f"{lhdn_setup_id.peppol_sync_api_base_url}/v1/lookup/peppol_participants",
                            params=json.dumps(peppol_lookup_dict),
                            headers=headers)

        if res.status_code == 200:
            res = res.json()
            res = res.get('ok')
            participants_data = res.get('participants')
            if len(res.get('participants')):
                if self.peppol_id == self.peppol_lookup_id:
                    self.peppol_status = 'registered'
                    self._cr.commit()
                raise UserError(_(f"Participants Found ==> {json.dumps(participants_data, indent=4)}"))
            else:
                raise UserError((f"Peppol Id {self.peppol_lookup_id} is Not Found"))
        elif res.status_code == 404:
            raise UserError((f"Peppol Id {self.peppol_lookup_id} is not found"))
        else:
            raise UserError((f"Geetings some error while performing this operations ==> {res.text}"))
