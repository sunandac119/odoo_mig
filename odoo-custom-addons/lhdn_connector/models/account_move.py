from odoo import api, fields, models, _
import requests
import json
from odoo.exceptions import MissingError, ValidationError, AccessError, UserError

from odoo.tools import DEFAULT_SERVER_DATE_FORMAT, float_repr, is_html_empty, html2plaintext, cleanup_xml_node
from lxml import etree
from datetime import datetime, timedelta
import base64
import hashlib
import logging
import xml.etree.ElementTree as ET
import time
from cryptography.hazmat.primitives import hashes, serialization
from cryptography.hazmat.primitives.asymmetric import padding
from cryptography.hazmat.primitives.serialization import load_pem_private_key
from cryptography import x509
from cryptography.hazmat.backends import default_backend
import os
import pytz
import re
import time
from math import ceil
import shutil

# import os
# import logging
# _logger = logging.getLogger("LHDN")
_logger = logging.getLogger('Erros_ocuureds====>')

INVOICE_TYPE_CODE = {
    'out_invoice': "01",
    'out_refund': "02",
    'in_invoice': "11",
    'in_refund': "12"

}

PEPPOL_DOCTYPE_ID = {
    'out_invoice': "urn:oasis:names:specification:ubl:schema:xsd:Invoice-2::Invoice##urn:peppol:pint:billing-1@my-1::2.1",
    'out_refund': "urn:oasis:names:specification:ubl:schema:xsd:CreditNote-2::CreditNote##urn:peppol:pint:billing-1@my-1::2.1",
    'in_invoice': "urn:oasis:names:specification:ubl:schema:xsd:Invoice-2::Invoice##urn:peppol:pint:selfbilling-1@my-1::2.1",
    'in_refund': "urn:oasis:names:specification:ubl:schema:xsd:CreditNote-2::CreditNote##urn:peppol:pint:selfbilling-1@my-1::2.1"
}

PEPPOL_PROCESS_ID = {
    'out_invoice': "urn:peppol:bis:billing",
    'out_refund': "urn:peppol:bis:billing",
    'in_invoice': "urn:peppol:bis:selfbilling",
    'in_refund': "urn:peppol:bis:selfbilling"
}

PEPPOL_INVOICE_TYPE_CODE = {
    'out_invoice': 380,
    'out_refund': 381,
    'in_invoice': 380,
    'in_refund': 381
}


class AccountMove(models.Model):
    _inherit = 'account.move'

    lhdn_uuid = fields.Char(string="LHDN UUID", copy=False)
    lhdn_submission_uid = fields.Char(string="Submission UID", copy=False)
    lhdn_invoice_status = fields.Selection([("new", "NEW"),
                                            ("submitted", "Submitted"),
                                            ("validated", "Validated"),
                                            ("error", "Error"),
                                            ("warning", "Warning"),
                                            ("cancelled", "Cancelled"),
                                            ("rejected", "Rejected")], string="LHDN Invoice status", default="new",
                                           copy=False)

    lhdn_document_cancellation_reason = fields.Char("LHDN Documents Cancellation / Rejections reason", copy=False)
    lhdn_documents_error = fields.Char(string="LHDN Documents error", copy=False)
    invoice_issue_time = fields.Datetime(string="Invoice Date & Time", copy=False)
    is_created_from_lhdn_uuid = fields.Boolean(string="Is Created from the LHDN UUID?", copy=False)
    origin_lhdn_uuid = fields.Char(string="Origin LHDN UUID", copy=False)
    is_lhdn_pos_retail_combine_invoice = fields.Boolean(string="Is LHDN Pos Retail combine Invoice", copy=False)

    lhdn_json_data = fields.Char(string="LHDN JSON data", copy=False)
    is_sended_in_peppol = fields.Boolean(string="Is Sended in Peppol Network?", default=False, copy=False)
    lhdn_xml_attachment = fields.Many2one('ir.attachment', string="LHDN XML Files", copy=False)
    peppol_xml_attachment = fields.Many2one('ir.attachment', string="Peppol XML Files", copy=False)
    is_created_from_peppol_received_docs = fields.Boolean(
        string="Is created from the Peppol Network Received Documents?", copy=False)
    peppol_received_docs_ref = fields.Char(string="Peppol Received Documents Reference", copy=False)
    lhdn_longid = fields.Char("LHDN Docs LongId", copy=False)
    lhdn_base_url = fields.Char("LHDN Base Url")
    is_created_from_ai = fields.Boolean(string="Is Created From AI?")
    portal_ai_inv_number = fields.Char(string="Portal ai inv number")
    is_created_from_sftp = fields.Boolean(string="Is Created From SFTP?")

    def action_post(self):
        # inherit of the function from account.move to validate a new tax and the priceunit of a downpayment
        res = super(AccountMove, self).action_post()
        self.invoice_issue_time = fields.Datetime().now()
        return res

    def lhdn_api_json_format_preparation(self):
        if not self.invoice_issue_time:
            raise UserError(_("Fill the Invocies issue time fields data"))

        user_tz = self.env.user.tz or 'UTC'
        local_tz = pytz.timezone(user_tz)
        invoice_issue_time_locals_timezone = self.invoice_issue_time.astimezone(local_tz).strftime("%I:%M:%SZ")
        api_dict = {
            "ID": [
                {
                    "_": self.portal_ai_inv_number if self.portal_ai_inv_number else self.name
                }
            ],
            "IssueDate": [
                {
                    "_": self.invoice_date.strftime("%Y-%m-%d")
                }
            ],
            "IssueTime": [
                {
                    "_": invoice_issue_time_locals_timezone
                }
            ],
            "InvoiceTypeCode": [
                {
                    "_": INVOICE_TYPE_CODE[self.move_type],
                    "listVersionID": "1.0"
                }
            ],
            "DocumentCurrencyCode": [
                {
                    "_": self.currency_id.name
                }
            ],
            # OPTIONALS FIELDS DATA
            "InvoicePeriod": [
                {
                    "StartDate": [
                        {
                            "_": self.invoice_date.strftime("%Y-%m-%d")
                        }
                    ],
                    "EndDate": [
                        {
                            "_": self.invoice_date.strftime("%Y-%m-%d")
                        }
                    ],
                    # "Description": [
                    #     {
                    #         "_": "Monthly"
                    #     }
                    # ]
                }
            ],

            # Mandatory where Applicables
            # "AdditionalDocumentReference": [
            #     {
            #         "ID": [
            #             {
            #                 "_": "E12345678912"
            #             }
            #         ],
            #         "DocumentType": [
            #             {
            #                 "_": "CustomsImportForm"
            #             }
            #         ]
            #     },
            #     {
            #         "ID": [
            #             {
            #                 "_": "ASEAN-Australia-New Zealand FTA (AANZFTA)"
            #             }
            #         ],
            #         "DocumentType": [
            #             {
            #                 "_": "FreeTradeAgreement"
            #             }
            #         ],
            #         "DocumentDescription": [
            #             {
            #                 "_": "Sample Description"
            #             }
            #         ]
            #     },
            #     {
            #         "ID": [
            #             {
            #                 "_": "E12345678912"
            #             }
            #         ],
            #         "DocumentType": [
            #             {
            #                 "_": "K2"
            #             }
            #         ]
            #     },
            #     {
            #         "ID": [
            #             {
            #                 "_": "CIF"
            #             }
            #         ]
            #     }
            # ],
        }

        if self.move_type in ['out_refund', 'in_refund']:
            if not self.origin_lhdn_uuid:
                raise UserError(_("Required to Fill Up The LHDN Origin ID"))
            if not self.reversed_entry_id:
                if self.move_type in ['out_refund']:
                    raise UserError(_("Required to Fill Up Theas Customer Reference fields data"))
                if self.move_type in ['in_refund']:
                    raise UserError(_("Required to Fill Up The Bill Reference fields data"))
            api_dict.update({
                "BillingReference": [
                    {
                        # "AdditionalDocumentReference": [
                        #     {
                        #         "ID": [
                        #             {
                        #                 "_": "E12345678912"
                        #             }
                        #         ]
                        #     }
                        # ],
                        "InvoiceDocumentReference": [
                            {
                                "UUID": [
                                    {
                                        "_": self.origin_lhdn_uuid
                                    }
                                ],
                                "inv_number": [
                                    {
                                        "_": self.reversed_entry_id.name
                                    }
                                ]
                            }
                        ]

                    }
                ],
            })

        asp_msic_code_id = ""
        asp_party_id = ""

        if self.move_type in ["out_invoice", "out_refund"]:
            lhdn_setup_id = self.env['lhdn.setup'].search([], limit=1)
            asp_msic_code_id = lhdn_setup_id.my_company_msic_code_id
            asp_party_id = self.env.company.partner_id
        if self.move_type in ["in_invoice", "in_refund"]:
            asp_msic_code_id = self.partner_id.msic_code_id
            asp_party_id = self.partner_id

        api_dict.update(
            {
                "AccountingSupplierParty": [
                    {
                        # OPTIONALS
                        # "AdditionalAccountID": [
                        #     {
                        #         "_": "CPT-CCN-W-211111-KL-000002",
                        #         "schemeAgencyName": "CertEX"
                        #     }
                        # ],
                        "Party": [
                            {
                                "IndustryClassificationCode": [
                                    {
                                        "_": asp_msic_code_id.code,
                                        "name": asp_msic_code_id.name
                                    }
                                ],
                                "PartyIdentification": [
                                    {
                                        "ID": [
                                            {
                                                "_": asp_party_id.tin,
                                                "schemeID": "TIN"
                                            }
                                        ]
                                    },
                                    {
                                        "ID": [
                                            {
                                                "_": asp_party_id.brn,
                                                "schemeID": "BRN"
                                            }
                                        ]
                                    },
                                    {
                                        "ID": [
                                            {
                                                "_": asp_party_id.sst or "N/A",
                                                "schemeID": "SST"
                                            }
                                        ]
                                    }
                                ],
                                "PostalAddress": [
                                    {
                                        "CityName": [
                                            {
                                                "_": asp_party_id.city
                                            }
                                        ],
                                        "PostalZone": [
                                            {
                                                "_": asp_party_id.zip
                                            }
                                        ],
                                        "CountrySubentityCode": [
                                            {
                                                "_": asp_party_id.state_id.code
                                            }
                                        ],
                                        "AddressLine": [
                                            {
                                                "Line": [
                                                    {
                                                        "_": asp_party_id.street
                                                    }
                                                ]
                                            },
                                            {
                                                "Line": [
                                                    {
                                                        "_": asp_party_id.street2
                                                    }
                                                ]
                                            },
                                            # {
                                            #     "Line": [
                                            #         {
                                            #             "_": "Persiaran Jaya"
                                            #         }
                                            #     ]
                                            # }
                                        ],
                                        "Country": [
                                            {
                                                "IdentificationCode": [
                                                    {
                                                        "_": "MYS",
                                                        "listID": "ISO3166-1",
                                                        "listAgencyID": "6"
                                                    }
                                                ]
                                            }
                                        ]
                                    }
                                ],
                                "PartyLegalEntity": [
                                    {
                                        "RegistrationName": [
                                            {
                                                "_": asp_party_id.name
                                            }
                                        ]
                                    }
                                ],
                                "Contact": [
                                    {
                                        "Telephone": [
                                            {
                                                "_": asp_party_id.phone
                                            }
                                        ],
                                        "ElectronicMail": [
                                            {
                                                "_": asp_party_id.email
                                            }
                                        ]
                                    }
                                ]
                            }
                        ]
                    }
                ],
            }
        )

        acp_party_id = ""
        if self.move_type in ["out_invoice", "out_refund"]:
            acp_party_id = self.partner_id
        if self.move_type in ["in_invoice", "in_refund"]:
            acp_party_id = self.env.company.partner_id

        api_dict.update(
            {
                "AccountingCustomerParty": [
                    {
                        "Party": [
                            {
                                "PostalAddress": [
                                    {
                                        "CityName": [
                                            {
                                                "_": acp_party_id.city
                                            }
                                        ],
                                        "PostalZone": [
                                            {
                                                "_": acp_party_id.zip
                                            }
                                        ],
                                        "CountrySubentityCode": [
                                            {
                                                "_": acp_party_id.state_id.code
                                            }
                                        ],
                                        "AddressLine": [
                                            {
                                                "Line": [
                                                    {
                                                        "_": acp_party_id.street
                                                    }
                                                ]
                                            },
                                            {
                                                "Line": [
                                                    {
                                                        "_": acp_party_id.street2
                                                    }
                                                ]
                                            },
                                            # {
                                            #     "Line": [
                                            #         {
                                            #             "_": "Persiaran Jaya"
                                            #         }
                                            #     ]
                                            # }
                                        ],
                                        "Country": [
                                            {
                                                "IdentificationCode": [
                                                    {
                                                        "_": "MYS",
                                                        "listID": "ISO3166-1",
                                                        "listAgencyID": "6"
                                                    }
                                                ]
                                            }
                                        ]
                                    }
                                ],
                                "PartyLegalEntity": [
                                    {
                                        "RegistrationName": [
                                            {
                                                "_": acp_party_id.name
                                            }
                                        ]
                                    }
                                ],
                                "PartyIdentification": [
                                    {
                                        "ID": [
                                            {
                                                "_": acp_party_id.tin,
                                                "schemeID": "TIN"
                                            }
                                        ]
                                    },
                                    {
                                        "ID": [
                                            {
                                                "_": acp_party_id.brn,
                                                "schemeID": "BRN"
                                            }
                                        ]
                                    }
                                ],
                                "Contact": [
                                    {
                                        "Telephone": [
                                            {
                                                "_": acp_party_id.phone
                                            }
                                        ],
                                        "ElectronicMail": [
                                            {
                                                "_": acp_party_id.email
                                            }
                                        ]
                                    }
                                ]
                            }
                        ]
                    }
                ],
            }
        )

        delivery_party_id = ""
        if self.move_type in ["out_invoice", "out_refund"]:
            delivery_party_id = self.partner_shipping_id
        if self.move_type in ["in_invoice", "in_refund"]:
            delivery_party_id = self.env.company.partner_id
        api_dict.update(
            {
                "Delivery": [
                    {
                        "DeliveryParty": [
                            {
                                "PostalAddress": [
                                    {
                                        "CityName": [
                                            {
                                                "_": delivery_party_id.city
                                            }
                                        ],
                                        "PostalZone": [
                                            {
                                                "_": delivery_party_id.zip
                                            }
                                        ],
                                        "CountrySubentityCode": [
                                            {
                                                "_": delivery_party_id.state_id.code
                                            }
                                        ],
                                        "AddressLine": [
                                            {
                                                "Line": [
                                                    {
                                                        "_": delivery_party_id.street
                                                    }
                                                ]
                                            },
                                            {
                                                "Line": [
                                                    {
                                                        "_": delivery_party_id.street2
                                                    }
                                                ]
                                            },
                                            # {
                                            #     "Line": [
                                            #         {
                                            #             "_": "Persiaran Jaya"
                                            #         }
                                            #     ]
                                            # }
                                        ],
                                        "Country": [
                                            {
                                                "IdentificationCode": [
                                                    {
                                                        "_": "MYS",
                                                        "listID": "ISO3166-1",
                                                        "listAgencyID": "6"
                                                    }
                                                ]
                                            }
                                        ]
                                    }
                                ],
                                "PartyLegalEntity": [
                                    {
                                        "RegistrationName": [
                                            {
                                                "_": delivery_party_id.name
                                            }
                                        ]
                                    }
                                ],
                                "PartyIdentification": [
                                    {
                                        "ID": [
                                            {
                                                "_": delivery_party_id.tin,
                                                "schemeID": "TIN"
                                            }
                                        ]
                                    },
                                    {
                                        "ID": [
                                            {
                                                "_": delivery_party_id.brn,
                                                "schemeID": "BRN"
                                            }
                                        ]
                                    }
                                ],
                            }
                        ],
                        # "Shipment": [
                        #     {
                        #         "ID": [
                        #             {
                        #                 "_": "1234"
                        #             }
                        #         ],
                        #         "FreightAllowanceCharge": [
                        #             {
                        #                 "ChargeIndicator": [
                        #                     {
                        #                         "_": true
                        #                     }
                        #                 ],
                        #                 "AllowanceChargeReason": [
                        #                     {
                        #                         "_": "Service charge"
                        #                     }
                        #                 ],
                        #                 "Amount": [
                        #                     {
                        #                         "_": 100,
                        #                         "currencyID": "MYR"
                        #                     }
                        #                 ]
                        #             }
                        #         ]
                        #     }
                        # ]

                    }
                ],

                # OPTIONALS DATAS
                # "PaymentMeans": [
                #     {
                #         "PaymentMeansCode": [
                #             {
                #                 "_": "01"
                #             }
                #         ],
                #         "PayeeFinancialAccount": [
                #             {
                #                 "ID": [
                #                     {
                #                         "_": "1234567890123"
                #                     }
                #                 ]
                #             }
                #         ]
                #     }
                # ],
                # "PaymentTerms": [
                #     {
                #         "Note": [
                #             {
                #                 "_": "Payment method is cash"
                #             }
                #         ]
                #     }
                # ],
                # "PrepaidPayment": [
                #     {
                #         "ID": [
                #             {
                #                 "_": "E12345678912"
                #             }
                #         ],
                #         "PaidAmount": [
                #             {
                #                 "_": 1.00,
                #                 "currencyID": "MYR"
                #             }
                #         ],
                #         "PaidDate": [
                #             {
                #                 "_": "2000-01-01"
                #             }
                #         ],
                #         "PaidTime": [
                #             {
                #                 "_": "12:00:00Z"
                #             }
                #         ]
                #     }
                # ],
                # "AllowanceCharge": [
                #     {
                #         "ChargeIndicator": [
                #             {
                #                 "_": false
                #             }
                #         ],
                #         "AllowanceChargeReason": [
                #             {
                #                 "_": "Sample Description"
                #             }
                #         ],
                #         "Amount": [
                #             {
                #                 "_": 100,
                #                 "currencyID": "MYR"
                #             }
                #         ]
                #     },
                #     {
                #         "ChargeIndicator": [
                #             {
                #                 "_": true
                #             }
                #         ],
                #         "AllowanceChargeReason": [
                #             {
                #                 "_": "Service charge"
                #             }
                #         ],
                #         "Amount": [
                #             {
                #                 "_": 100,
                #                 "currencyID": "MYR"
                #             }
                #         ]
                #     }
                # ],
            }
        )

        api_dict.update(
            {
                "TaxTotal": [
                    {
                        "TaxAmount": [
                            {
                                "_": self.amount_tax,
                                "currencyID": self.currency_id.name
                            }
                        ],
                        "TaxSubtotal": [
                            {
                                "TaxableAmount": [
                                    {
                                        "_": self.amount_untaxed,
                                        "currencyID": self.currency_id.name
                                    }
                                ],
                                "TaxAmount": [
                                    {
                                        "_": self.amount_tax,
                                        "currencyID": self.currency_id.name
                                    }
                                ],
                                # Mandatory if tax exemption is applicable
                                "TaxCategory": [
                                    {
                                        "ID": [
                                            {
                                                "_": "01"
                                            }
                                        ],
                                        "TaxScheme": [
                                            {
                                                "ID": [
                                                    {
                                                        "_": "OTH",
                                                        "schemeID": "UN/ECE 5153",
                                                        "schemeAgencyID": "6"
                                                    }
                                                ]
                                            }
                                        ]
                                    }
                                ]
                            }
                        ]
                    }
                ],
            }
        )

        api_dict.update(
            {
                "LegalMonetaryTotal": [
                    {
                        # OPTIONALS DATAS
                        "LineExtensionAmount": [
                            {
                                "_": self.amount_untaxed,
                                "currencyID": self.currency_id.name
                            }
                        ],
                        "TaxExclusiveAmount": [
                            {
                                "_": self.amount_untaxed,
                                "currencyID": self.currency_id.name
                            }
                        ],
                        "TaxInclusiveAmount": [
                            {
                                "_": self.amount_total,
                                "currencyID": self.currency_id.name
                            }
                        ],
                        # "AllowanceTotalAmount": [
                        #     {
                        #         "_": 1436.50,
                        #         "currencyID":self.currency_id.name
                        #     }
                        # ],
                        # "ChargeTotalAmount": [
                        #     {
                        #         "_": 1436.50,
                        #         "currencyID": self.currency_id.name
                        #     }
                        # ],
                        # "PayableRoundingAmount": [
                        #     {
                        #         "_": 0.30,
                        #         "currencyID": self.currency_id.name
                        #     }
                        # ],
                        "PayableAmount": [
                            {
                                "_": self.amount_total,
                                "currencyID": self.currency_id.name
                            }
                        ]
                    }
                ],
            }
        )
        invoices_lines = []
        for line in self.invoice_line_ids:
            if not line.product_id.lhdn_classification_id:
                raise UserError(_(f"LHDN Classification was not setted into the products ==> {line.product_id.name}"))
            # if not line.tax_ids:
            #     raise UserError(_(f"Tax was not setted into the products line ==> {line.product_id.name}"))
            invoices_lines.append(
                {
                    "ID": [
                        {
                            "_": line.id
                        }
                    ],
                    "InvoicedQuantity": [
                        {
                            "_": line.quantity,
                            "unitCode": "C62"
                        }
                    ],
                    "LineExtensionAmount": [
                        {
                            "_": line.price_subtotal,
                            "currencyID": line.currency_id.name
                        }
                    ],
                    # "AllowanceCharge": [
                    #     {
                    #         "ChargeIndicator": [
                    #             {
                    #                 "_": false
                    #             }
                    #         ],
                    #         "AllowanceChargeReason": [
                    #             {
                    #                 "_": "Sample Description"
                    #             }
                    #         ],
                    #         "MultiplierFactorNumeric": [
                    #             {
                    #                 "_": 0.15
                    #             }
                    #         ],
                    #         "Amount": [
                    #             {
                    #                 "_": 100,
                    #                 "currencyID": "MYR"
                    #             }
                    #         ]
                    #     },
                    #     {
                    #         "ChargeIndicator": [
                    #             {
                    #                 "_": true
                    #             }
                    #         ],
                    #         "AllowanceChargeReason": [
                    #             {
                    #                 "_": "Sample Description"
                    #             }
                    #         ],
                    #         "MultiplierFactorNumeric": [
                    #             {
                    #                 "_": 0.10
                    #             }
                    #         ],
                    #         "Amount": [
                    #             {
                    #                 "_": 100,
                    #                 "currencyID": "MYR"
                    #             }
                    #         ]
                    #     }
                    # ],
                    "TaxTotal": [
                        {
                            "TaxAmount": [
                                {
                                    "_": line.price_total - line.price_subtotal,
                                    "currencyID": line.currency_id.name
                                }
                            ],
                            "TaxSubtotal": [
                                {
                                    "TaxableAmount": [
                                        {
                                            "_": line.price_subtotal,
                                            "currencyID": line.currency_id.name
                                        }
                                    ],
                                    "TaxAmount": [
                                        {
                                            "_": line.price_total - line.price_subtotal,
                                            "currencyID": line.currency_id.name
                                        }
                                    ],
                                    "TaxCategory": [
                                        {
                                            "ID": [
                                                {
                                                    "_": "01"
                                                }
                                            ],
                                            "Percent": [
                                                {
                                                    "_": sum(line.tax_ids.mapped('amount'))
                                                }
                                            ],
                                            "TaxScheme": [
                                                {
                                                    "ID": [
                                                        {
                                                            "_": "01",
                                                            "schemeID": "UN/ECE 5153",
                                                            "schemeAgencyID": "6"
                                                        }
                                                    ]
                                                }
                                            ],
                                            # "TaxExemptionReason": [
                                            #     {
                                            #         "_": "Exempt New Means of Transport"
                                            #     }
                                            # ]
                                        }
                                    ]
                                }
                            ]
                        }
                    ],
                    "Item": [
                        {
                            "CommodityClassification": [
                                {
                                    "ItemClassificationCode": [
                                        {
                                            "_": line.product_id.lhdn_classification_id.code,
                                            "listID": "PTC"
                                        }
                                    ]
                                },
                                {
                                    "ItemClassificationCode": [
                                        {
                                            "_": line.product_id.lhdn_classification_id.code,
                                            "listID": "CLASS"
                                        }
                                    ]
                                }
                            ],
                            "Description": [
                                {
                                    "_": line.name
                                }
                            ],
                            # "OriginCountry": [
                            #     {
                            #         "IdentificationCode": [
                            #             {
                            #                 "_": "MYS"
                            #             }
                            #         ]
                            #     }
                            # ]
                        }
                    ],
                    "Price": [
                        {
                            "PriceAmount": [
                                {
                                    "_": line.price_unit,
                                    "currencyID": line.currency_id.name
                                }
                            ]
                        }
                    ],
                    "ItemPriceExtension": [
                        {
                            "Amount": [
                                {
                                    "_": line.quantity * line.price_unit,
                                    "currencyID": line.currency_id.name
                                }
                            ]
                        }
                    ]
                }
            )

        api_dict.update(
            {
                "InvoiceLine": invoices_lines
            }
        )

        return api_dict

    def lhdn_token_generation(self, client_id, client_secret, lhdn_setup_id):
        res = {}
        if lhdn_setup_id.lhdn_token and datetime.now() < lhdn_setup_id.lhdn_token_updateds_time + timedelta(minutes=55):
            res['access_token'] = lhdn_setup_id.lhdn_token
        else:
            lhdn_base_url = lhdn_setup_id.lhdn_sandbox_base_url if lhdn_setup_id.lhdn_connection_server_type == 'sandbox' else lhdn_setup_id.lhdn_production_base_url
            # Froms the AccountingSupplierParty
            # onbehalfof_tin = "C20962415090"
            headers = {
                # 'grant_type': 'client_credentials', 'scope': 'InvoicingAPI',
                'Content-Type': 'application/x-www-form-urlencoded',
                # 'onbehalfof': onbehalfof_tin
            }
            payload = {'client_id': client_id,
                       'client_secret': client_secret,
                       'grant_type': 'client_credentials',
                       'scope': 'InvoicingAPI',
                       # 'onbehalfof': onbehalfof_tin,
                       # 'Content-Type': 'application/x-www-form-urlencoded'
                       }
            res = requests.post(lhdn_base_url + '/connect/token', data=payload,
                                headers=headers)
            res = res.json()
            if res.get('access_token'):
                lhdn_setup_id.lhdn_token = res.get('access_token')
                lhdn_setup_id.lhdn_token_updateds_time = datetime.now()
                self._cr.commit()
        return res

    def generate_document_hash(self, xml_content_base64_string):
        # Hash the XML content using SHA-256
        sha256_hash = hashlib.sha256(xml_content_base64_string).hexdigest()
        return sha256_hash

    def generate_digital_signature(self, api_dict):
        # Fors Invocies purpose
        if self.move_type in ['out_invoice', 'out_refund']:
            customization_id = "urn:peppol:pint:billing-1@my-1"
            profile_id = "urn:peppol:bis:billing"
        else:
            # Fors an Bills Purpose
            # print()
            customization_id = "urn:peppol:pint:selfbilling-1@my-1"
            profile_id = "urn:peppol:bis:selfbilling"

        vals = {'vals': api_dict, 'is_contains_digi_sign': False, 'customization_id': customization_id,
                'profile_id': profile_id}
        xml_content_for_digi_sign = self.env['ir.qweb']._render("lhdn_connector.ubl_21_lhdn_Invoice", vals)

        root = etree.fromstring(xml_content_for_digi_sign)

        # # Canonicalize using xml-c14n11
        canonicalized_xml = etree.tostring(root, method="c14n", exclusive=False, with_comments=False).decode()
        canonicalized_xml = canonicalized_xml.replace('\n', '')
        canonicalized_xml = ''.join(canonicalized_xml.split())

        # xml_content_for_digi_sign = etree.tostring(cleanup_xml_node(xml_content_for_digi_sign), xml_declaration=True,
        #                                            encoding='UTF-8')

        # # Hash the canonicalized document using SHA-256
        # sha256_hash = hashlib.sha256(xml_content_for_digi_sign).digest()
        #
        # # Encode the hashed value to Base64
        # docDigest = base64.b64encode(sha256_hash).decode('utf-8')

        # Hash the canonicalized document using SHA-256
        sha256_hash = hashlib.sha256(canonicalized_xml.encode('utf-8'))
        hex_dig = sha256_hash.hexdigest()

        # Convert the SHA-256 hash from HEX to Base64
        docDigest = base64.b64encode(bytes.fromhex(hex_dig)).decode()

        # # Load the private key from a file (PEM format)
        pk_path_local = "/Users/onlymac/workspace/odoo_v17/custom_addons/ap_addon_17/private_key.pem"
        pk_path_server = "/home/ubuntu/private_key.pem"
        pk_final_path = False
        password = False
        if os.path.exists(pk_path_local):
            pk_final_path = pk_path_local
            password = "yash"
        elif os.path.exists(pk_path_server):
            pk_final_path = pk_path_server
            password = "lhdn"
        else:
            raise UserError("Please set an valida path for the private_key.pem into the code")

        # Load the private key from a file (PEM format)
        with open(pk_final_path, 'rb') as key_file:
            private_key = load_pem_private_key(key_file.read(), password=password.encode(), backend=default_backend())

        hash_bytes = base64.b64decode(docDigest)
        # Sign the hash with the private key using RSA-SHA256
        signature = private_key.sign(
            hash_bytes,
            padding.PKCS1v15(),
            hashes.SHA256()
        )

        # Encode the signature to Base64
        sig = base64.b64encode(signature).decode()

        cert_path_local = "/Users/onlymac/workspace/odoo_v17/custom_addons/ap_addon_17/certificate.pem"
        cert_path_server = "/home/ubuntu/certificate.pem"
        cert_final_path = False
        if os.path.exists(cert_path_local):
            cert_final_path = cert_path_local
        elif os.path.exists(cert_path_server):
            cert_final_path = cert_path_server
        else:
            raise UserError("Please set an valida path for the certificate.pem into the code")
        # Load the signing certificate from a file (PEM format)
        with open(cert_final_path, 'rb') as cert_file:
            certificate = x509.load_pem_x509_certificate(cert_file.read(), backend=default_backend())

        # # Hash the signing certificate using SHA-256
        # cert_sha256_hash = hashlib.sha256(certificate.public_bytes(encoding=serialization.Encoding.PEM)).digest()

        # Hash the certificate using SHA-256
        digest = hashes.Hash(hashes.SHA256(), backend=default_backend())
        digest.update(certificate.public_bytes(encoding=serialization.Encoding.PEM))
        certificate_hash = digest.finalize()

        # Encode the certificate hash using Base64
        base64_encoded_cert_hash = cert_digest = base64.b64encode(certificate_hash).decode('utf-8')

        signed_props_vals = {
            'signing_time': datetime.now().strftime("%Y-%m-%dT%H:%M:%SZ"),
            'digest_value': cert_digest,
            'x509_issuer_name': "Contoso Malaysia Sdn Bhd",
            'x509_serial_number': certificate.serial_number,
            'customization_id': customization_id,
            'profile_id': profile_id
        }
        signed_properties_xml_content = self.env['ir.qweb']._render("lhdn_connector.signed_properties_template",
                                                                    signed_props_vals)

        # signed_properties_xml_content = etree.tostring(cleanup_xml_node(xml_content_for_digi_sign),
        #                                                xml_declaration=True,
        #                                                encoding='UTF-8')

        root = etree.fromstring(signed_properties_xml_content)

        # # Canonicalize using xml-c14n11
        canonicalized_xml = etree.tostring(root, method="c14n", exclusive=False, with_comments=False).decode()
        canonicalized_xml = canonicalized_xml.replace('\n', '')
        signed_properties_xml_content = ''.join(canonicalized_xml.split())

        # # Hash the linearized XML block using SHA-256
        # signed_properties_sha256_hash = hashlib.sha256(signed_properties_xml_content).digest()
        #
        # # Encode the hashed value using HEX-to-Base64
        # signed_properties_hex_to_base64_encoded_hash = base64.b64encode(signed_properties_sha256_hash).decode('utf-8')

        digest = hashes.Hash(hashes.SHA256(), backend=default_backend())
        digest.update(signed_properties_xml_content.encode())
        signed_properties_hash = digest.finalize()

        # The resulting hash to be used as PropsDigest
        props_digest_value = base64.b64encode(signed_properties_hash).decode()

        signed_props_vals.update({
            'signed_propes_digest_value': props_digest_value,
            'signed_data_digest_values': docDigest,
            'signature_value': sig,

        })
        return signed_props_vals

    def send_validated_invoice_to_peppolsync_server(self, lhdn_setup_id):
        xml_datas = self.attachments_ids.filterd(lambda a: "lhdn" in a.name)[0].datas.decode(
            'utf-8') if self.attachments_ids.filterd(lambda a: "lhdn" in a.name) else ""
        peppolsync_data_dict = {
            'api_client_id': lhdn_setup_id.peppol_sync_api_client_id,
            'api_client_password': lhdn_setup_id.peppol_sync_api_client_password,
            'inv_number': self.name,
            'lhdn_json_data': self.lhdn_json_data,
            'xml_data': xml_datas,
            'inv_total_amount': self.amount_total,
            'lhdn_uuid': self.lhdn_uuid,
            'lhdn_submission_uid': self.submission_uid,
            # 'lhdn_document_status': Needs to thinks ands addings becase of the peppolsysncs needs to addings another status calleds "Vvalidated"
        }
        headers = {'Content-Type': 'application/json'}
        res = requests.post(f"{lhdn_setup_id.peppol_sync_api_base_url}/v1/send/direct_api_invoice",
                            params=json.dumps(peppolsync_data_dict),
                            headers=headers)

        return True

    def send_api_request(self, api_dict):
        use_peppol_documents_service = False
        xml_content_base64_string = False
        if self.partner_id.send_documents_via_peppol and self.move_type in ['out_invoice', 'out_refund', 'in_invoice',
                                                                            'in_refund']:
            if self.company_id.partner_id.peppol_status != 'registered':
                raise UserError(
                    _(f"Need to Register Your company partner ({self.company_id.partner_id.name}) in Peppol SML; GO To Companyies -> click on the partner-> Enable the button Automatically Send Documents via Peppol?"))
            else:
                use_peppol_documents_service = True
        # else:
        #     raise UserError(_(f"You not enabled the Peppol document sharing feature for the partners ==> {self.partner_id.name}. Go to Customers-> Enable the button Automatically Send Documents via Peppol?"))

        lhdn_setup_id = self.env['lhdn.setup'].search([], limit=1)
        lhdn_base_url = lhdn_setup_id.lhdn_sandbox_base_url if lhdn_setup_id.lhdn_connection_server_type == 'sandbox' else lhdn_setup_id.lhdn_production_base_url
        # res = ""
        if lhdn_setup_id.choose_submission_way == 'intermediate_api':
            headers = {'Content-Type': 'application/json'}
            data = {
                'client_id': lhdn_setup_id.peppol_sync_api_client_id,
                'client_password': lhdn_setup_id.peppol_sync_api_client_password,
                # 'tin':'100000342',
                'myinvoice_credential': {},
                # 'client_id': lhdn_setup_id.lhdn_api_client_id,
                #                              'client_secret': lhdn_setup_id.lhdn_api_client_password},
                "invoice_dict": [api_dict]
            }

            if self.move_type in ['out_invoice', 'out_refund']:
                asp_id = self.company_id.partner_id
                acp_id = self.partner_id
                asp_endpoint_id = self.company_id.partner_id.peppol_id.split(":")[1]
                acp_endpoint_id = self.partner_id.peppol_id.split(":")[1]
                asp_brn = self.company_id.partner_id.brn
                acp_brn = self.partner_id.brn

                asp_sst = self.company_id.partner_id.sst or "N/A"
                acp_sst = self.partner_id.sst or "N/A"

                asp_tin = self.company_id.partner_id.tin
                acp_tin = self.partner_id.tin
            else:
                asp_id = self.partner_id
                acp_id = self.company_id.partner_id
                asp_endpoint_id = self.partner_id.peppol_id.split(":")[1]
                acp_endpoint_id = self.company_id.partner_id.peppol_id.split(":")[1]
                asp_brn = self.partner_id.brn
                acp_brn = self.company_id.partner_id.brn

                asp_sst = self.partner_id.sst or "N/A"
                acp_sst = self.company_id.partner_id.sst or "N/A"

                asp_tin = self.partner_id.tin
                acp_tin = self.company_id.partner_id.tin

            peppol_invoice_type_code = PEPPOL_INVOICE_TYPE_CODE[self.move_type]

            if not asp_brn and not self.is_created_from_ai:
                raise UserError(_(f"Set the BRN Number for the {asp_id.name}"))
            if not acp_brn and not self.is_created_from_ai:
                raise UserError(_(f"Set the BRN Number for the {acp_id.name}"))

            # if not asp_sst:
            #     raise UserError(_(f"Set the SST Number for the {asp_id.name}"))
            # if not acp_sst:
            #     raise UserError(_(f"Set the SST Number for the {acp_id.name}"))

            if not asp_tin:
                raise UserError(_(f"Set the TIN Number for the {asp_id.name}"))
            if not acp_tin:
                raise UserError(_(f"Set the TIN Number for the {acp_id.name}"))

            peppol_tax_subtotal_group = []
            for line in self.invoice_line_ids:
                percent_tax_invoice_line = line.tax_ids[0].amount if line.tax_ids and line.tax_ids[0].amount else 0
                current_line_tax_percents_exist_in_group = False
                for taxLine in peppol_tax_subtotal_group:
                    current_tax_group_line_tax_percents = taxLine.get('TaxCategory').get('Percent')
                    if current_tax_group_line_tax_percents == percent_tax_invoice_line:
                        taxLine.get('TaxableAmount')['amount'] += line.price_subtotal
                        taxLine.get('TaxAmount')['amount'] += round(line.price_total - line.price_subtotal,2)
                        current_line_tax_percents_exist_in_group = True
                    # else:
                if not current_line_tax_percents_exist_in_group:
                    peppol_tax_subtotal_group.append({
                        'TaxableAmount': {'amount': line.price_subtotal, 'currency_id': line.currency_id.name},
                        'TaxAmount': {'amount':round(line.price_total - line.price_subtotal,2),
                                      'currency_id': line.currency_id.name},
                        'TaxCategory': {
                            'ID': 'T' if line.tax_ids and line.tax_ids[0].amount else 'E',
                            'Percent': line.tax_ids[0].amount if line.tax_ids and line.tax_ids[0].amount else 0
                        }
                    })

            peppol_vals = {
                'vals': api_dict,
                'is_for_peppol': True,
                'asp_endpoint_id': asp_endpoint_id,
                'acp_endpoint_id': acp_endpoint_id,
                'peppol_invoice_type_code': peppol_invoice_type_code,
                'acp_brn': acp_brn,
                'asp_brn': asp_brn,
                'asp_tin': asp_tin,
                'acp_tin': acp_tin,
                'asp_sst': asp_sst,
                'acp_sst': acp_sst,
                'peppol_tax_subtotal_group': peppol_tax_subtotal_group,
            }

            # Fors Invocies purpose
            if self.move_type in ['out_invoice', 'out_refund']:
                customization_id = "urn:peppol:pint:billing-1@my-1"
                profile_id = "urn:peppol:bis:billing"
            else:
                # Fors an Bills Purpose
                # print()
                customization_id = "urn:peppol:pint:selfbilling-1@my-1"
                profile_id = "urn:peppol:bis:selfbilling"
            peppol_vals.update({'customization_id': customization_id, 'profile_id': profile_id})
            data.update({'peppol_vals': peppol_vals})
            data.update({'move_type': self.move_type})
            data.update({'onbehalfof_tin': self.company_id.partner_id.tin})
            # res = requests.post(f"{lhdn_setup_id.peppol_sync_api_base_url}/v1/send_document", params=json.dumps(data),
            #                     headers=headers)
            res = requests.post(f"{lhdn_setup_id.peppol_sync_api_base_url}/v1/send_document", json=data,
                                headers=headers)
            res = res.json()
            if res.get('status_code') == 200:

                # headers = {'Content-Type': 'application/json'}

                data = {
                    'client_id': lhdn_setup_id.peppol_sync_api_client_id,
                    'client_password': lhdn_setup_id.peppol_sync_api_client_password,
                    'api_use': "myinvoice_api",
                    'tin': '100000342',
                    'peppol_credential': {},
                    'myinvoice_credential': {},
                    "invoice_dict": {'inv_number': self.name},
                    'onbehalfof_tin': self.company_id.partner_id.tin
                }

                get_documents_info = requests.post(f'{lhdn_setup_id.peppol_sync_api_base_url}/v1/get_document_details',
                                                   params=json.dumps(data),
                                                   headers=headers)
                submitted_documents_info = get_documents_info.json()
                if not submitted_documents_info.get('error'):
                    submitted_documents_info = submitted_documents_info.get('Result')
                    self.lhdn_longid = submitted_documents_info.get('longId')
                    self.lhdn_base_url = lhdn_base_url
                    _logger.info(f'Gets Documents informations ==> {submitted_documents_info}')
                    if submitted_documents_info.get('status') == 'Invalid':
                        self.lhdn_invoice_status = 'submitted'
                        self.message_post(body=_(
                            f"LHDN Direct API ==> Documents Invalides Reason {submitted_documents_info}",
                            description=123))
                        self.lhdn_documents_error = "Submitted Documents was an Invalid,Please refere the Chatter"
                    elif submitted_documents_info.get('status') == 'Valid':
                        self.lhdn_invoice_status = 'validated'
                        self.lhdn_documents_error = ""

                    elif submitted_documents_info.get('status') == 'Submitted':
                        self.message_post(body=_(
                            f"LHDN Direct API ==> Documentss Gettings errors ==> {submitted_documents_info}",
                            description=123))
                        # Because of too lates response from the lhdn regardings the updatings the Valid status
                        self.lhdn_invoice_status = 'submitted'
                        self.lhdn_documents_error = "May be The Late Response from the LHDN Direct API need to fetch the status again"
                    else:
                        self.lhdn_invoice_status = 'submitted'
                        self.lhdn_documents_error = "May be The LHDN Take time to process your invoices, After some times need to fetch the status again"

                    self.lhdn_uuid = submitted_documents_info.get('uuid')  # docUUID
                    self.lhdn_submission_uid = submitted_documents_info.get('submissionUid')  # docSubmissionUID
                    self.message_post(body=_(
                        f"LHDN Intermediates API ==> Documents Submitted successfully", description=123))

                    # self.lhdn_invoice_status = 'validated'
                    # lhdn_doc_dict = res.get('myinvoice_result').get('myinvoice_result')[0]
                    # self.lhdn_uuid = lhdn_doc_dict['docUUID']
                    # self.lhdn_submission_uid = lhdn_doc_dict['docSubmissionUID']
                    # self.lhdn_documents_error = ""
                else:
                    self.lhdn_invoice_status = 'error'
                    temp_error_string = ""
                    if isinstance(submitted_documents_info.get('error'), list):
                        for i in submitted_documents_info.get('error'):
                            temp_error_string = temp_error_string + i + ';'
                    else:
                        temp_error_string = submitted_documents_info.get('error')
                    self.lhdn_documents_error = "LHDN Error==> " + json.dumps(temp_error_string)
                    self.message_post(body=_(f"{submitted_documents_info.get('error')}", description=123))
            elif res.get('status_code') == 409 and res.get('exist_record_data'):
                exist_records_data = res.get('exist_record_data')
                self.lhdn_invoice_status = 'submitted'
                self.lhdn_uuid = exist_records_data.get('lhdn_uuid')
                self.lhdn_submission_uid = exist_records_data.get('lhdn_submission_uid')
                self.lhdn_documents_error = "Click on the Fetch Status"
                self.message_post(body=_(res.get('error')))
            else:
                self.lhdn_invoice_status = 'error'
                temp_error_string = ""
                if isinstance(res.get('error'), list):
                    for i in res.get('error'):
                        temp_error_string = temp_error_string + i + ';'
                else:
                    temp_error_string = res.get('error')
                self.lhdn_documents_error = "LHDN Error==> " + str(temp_error_string)
                self.message_post(body=_(f"{res.get('error')}", description=123))
        else:
            # Direct API Submissions
            lhdn_token_generation = self.lhdn_token_generation(lhdn_setup_id.lhdn_api_client_id,
                                                               lhdn_setup_id.lhdn_api_client_password, lhdn_setup_id)
            lhdn_base_url = lhdn_setup_id.lhdn_sandbox_base_url if lhdn_setup_id.lhdn_connection_server_type == 'sandbox' else lhdn_setup_id.lhdn_production_base_url
            if lhdn_token_generation.get('access_token'):
                access_token = lhdn_token_generation.get('access_token')

                signed_props_value = self.generate_digital_signature(api_dict)

                vals = {'vals': api_dict, 'is_contains_digi_sign': True}
                vals.update(signed_props_value)
                xml_content = self.env['ir.qweb']._render("lhdn_connector.ubl_21_lhdn_Invoice", vals)
                xml_content = etree.tostring(cleanup_xml_node(xml_content), xml_declaration=True, encoding='UTF-8')
                _logger.info(f'This isthe as xmls fileas ==> {xml_content}')
                xml_content_base64_string = base64.b64encode(xml_content)

                # customization_id = vals.get('customization_id')
                # profile_id = vals.get('profile_id')
                # # , 'customization_id': customization_id, 'profile_id': profile_id

                if not self.company_id.partner_id.peppol_id:
                    raise UserError(
                        _(f"Required To Fill Up Thes partner id({self.company_id.partner_id.name})of the company's Peppol Id fields data"))
                if not self.partner_id.peppol_id:
                    raise UserError(
                        _(f"Required To Fill Up Thes Customer/Vndeto Id({self.partner_id.name}) Peppol Id fields data"))
                if self.move_type in ['out_invoice', 'out_refund']:
                    asp_id = self.company_id.partner_id
                    acp_id = self.partner_id
                    asp_endpoint_id = self.company_id.partner_id.peppol_id.split(":")[1]
                    acp_endpoint_id = self.partner_id.peppol_id.split(":")[1]
                    asp_brn = self.company_id.partner_id.brn
                    acp_brn = self.partner_id.brn

                    asp_sst = self.company_id.partner_id.sst or "N/A"
                    acp_sst = self.partner_id.sst or "N/A"

                    asp_tin = self.company_id.partner_id.tin
                    acp_tin = self.partner_id.tin
                else:
                    asp_id = self.partner_id
                    acp_id = self.company_id.partner_id
                    asp_endpoint_id = self.partner_id.peppol_id.split(":")[1]
                    acp_endpoint_id = self.company_id.partner_id.peppol_id.split(":")[1]
                    asp_brn = self.partner_id.brn
                    acp_brn = self.company_id.partner_id.brn

                    asp_sst = self.partner_id.sst or "N/A"
                    acp_sst = self.company_id.partner_id.sst or "N/A"

                    asp_tin = self.partner_id.tin
                    acp_tin = self.company_id.partner_id.tin

                peppol_invoice_type_code = PEPPOL_INVOICE_TYPE_CODE[self.move_type]

                if not asp_brn and not self.is_created_from_ai:
                    raise UserError(_(f"Set the BRN Number for the {asp_id.name}"))
                if not acp_brn and not self.is_created_from_ai:
                    raise UserError(_(f"Set the BRN Number for the {acp_id.name}"))

                # if not asp_sst:
                #     raise UserError(_(f"Set the SST Number for the {asp_id.name}"))
                # if not acp_sst:
                #     raise UserError(_(f"Set the SST Number for the {acp_id.name}"))

                if not asp_tin:
                    raise UserError(_(f"Set the TIN Number for the {asp_id.name}"))
                if not acp_tin:
                    raise UserError(_(f"Set the TIN Number for the {acp_id.name}"))

                peppol_tax_subtotal_group = []
                for line in self.invoice_line_ids:
                    peppol_tax_subtotal_group.append({
                        'TaxableAmount': {'amount': line.price_subtotal, 'currency_id': line.currency_id.name},
                        'TaxAmount': {'amount': line.price_total - line.price_subtotal,
                                      'currency_id': line.currency_id.name},
                        'TaxCategory': {
                            'ID': 'T' if line.tax_ids[0].amount else 'E',
                            'Percent': line.tax_ids[0].amount
                        }
                    })

                peppol_vals = {
                    'vals': api_dict,
                    'is_for_peppol': True,
                    'asp_endpoint_id': asp_endpoint_id,
                    'acp_endpoint_id': acp_endpoint_id,
                    'peppol_invoice_type_code': peppol_invoice_type_code,
                    'acp_brn': acp_brn,
                    'asp_brn': asp_brn,
                    'asp_tin': asp_tin,
                    'acp_tin': acp_tin,
                    'asp_sst': asp_sst,
                    'acp_sst': acp_sst,
                    'peppol_tax_subtotal_group': peppol_tax_subtotal_group,
                }
                peppol_vals.update(signed_props_value)
                # vals.update(signed_props_value)
                if self.move_type in ['out_invoice', 'in_invoice']:
                    peppol_xml_content = self.env['ir.qweb']._render("lhdn_connector.ubl_21_lhdn_Invoice", peppol_vals)
                else:
                    peppol_xml_content = self.env['ir.qweb']._render("lhdn_connector.peppol_21_credit_note",
                                                                     peppol_vals)

                peppol_xml_content = etree.tostring(cleanup_xml_node(peppol_xml_content), xml_declaration=True,
                                                    encoding='UTF-8')

                if self.lhdn_xml_attachment:
                    self.lhdn_xml_attachment.unlink()
                if self.peppol_xml_attachment:
                    self.peppol_xml_attachment.unlink()
                # Create the attachments Fors ans LHDN
                lhdn_attachment_vals = {
                    'name': f"lhdn_{self.name}.xml",
                    'type': 'binary',
                    'datas': xml_content_base64_string,
                    'res_model': 'account.move',
                    'res_id': self.id,
                    'mimetype': 'application/xml'
                }
                lhdn_xml_attachment = self.env['ir.attachment'].create(lhdn_attachment_vals)
                self.lhdn_xml_attachment = lhdn_xml_attachment.id

                # Create the attachments Fors an Peppol
                peppol_attachment_vals = {
                    'name': f"peppol_{self.name}.xml",
                    'type': 'binary',
                    'datas': base64.b64encode(peppol_xml_content),
                    'res_model': 'account.move',
                    'res_id': self.id,
                    'mimetype': 'application/xml'
                }
                peppol_xml_attachment = self.env['ir.attachment'].create(peppol_attachment_vals)
                self.peppol_xml_attachment = peppol_xml_attachment.id
                # self.peppol_xml_content_base64_string = base64.b64encode(peppol_xml_content)
                documents_list = []
                documents_list.append({"format": "XML",
                                       "documentHash": self.generate_document_hash(xml_content),
                                       "codeNumber": vals['vals']['ID'][0].get('_'),
                                       "document": xml_content_base64_string.decode("utf-8")
                                       })
                submit_headers = headers = {'Content-Type': 'application/json',
                                            'Authorization': f'Bearer {access_token}'}
                # This is only for the single documents submission
                submit_payload = {"documents": documents_list}

                submit_payload = json.dumps(submit_payload)
                # res = requests.get(
                #     lhdn_base_url + '/api/v1.0/taxpayer/validate/C2584563222?idType=BRN&idValue=202001234567',
                #     params={}, headers=submit_headers)

                result = requests.post(lhdn_base_url + '/api/v1.0/documentsubmissions', data=submit_payload,
                                       headers=submit_headers)

                result = result.json()

                if result.get('submissionUid'):
                    if result.get('acceptedDocuments'):
                        # Settings the response to the invocie

                        for acceptedDoc in result.get('acceptedDocuments'):
                            docUUID = acceptedDoc.get('uuid')
                            docSubmissionUID = result.get('submissionUid')

                            # time.sleep(12)

                            get_documents_info = requests.get(
                                lhdn_base_url + f'/api/v1.0/documents/{docUUID}/details',
                                headers={'Authorization': f'Bearer {access_token}'}, data={})
                            submitted_documents_info = get_documents_info.json()
                            self.lhdn_longid = submitted_documents_info.get('longId')
                            self.lhdn_base_url = lhdn_base_url
                            _logger.info(f'Gets Documents informations ==> {submitted_documents_info}')
                            if submitted_documents_info.get('status') == 'Invalid':
                                self.lhdn_invoice_status = 'submitted'
                                self.message_post(body=_(
                                    f"LHDN Direct API ==> Documents Invalides Reason {submitted_documents_info}",
                                    description=123))
                                self.lhdn_documents_error = "Submitted Documents was an Invalid,Please refere the Chatter"
                            elif submitted_documents_info.get('status') == 'Valid':
                                self.lhdn_invoice_status = 'validated'
                                self.lhdn_documents_error = ""

                            elif submitted_documents_info.get('status') == 'Submitted':
                                self.message_post(body=_(
                                    f"LHDN Direct API ==> Documentss Gettings errors ==> {submitted_documents_info}",
                                    description=123))
                                # Because of too lates response from the lhdn regardings the updatings the Valid status
                                self.lhdn_invoice_status = 'submitted'
                                self.lhdn_documents_error = "May be The Late Response from the LHDN Direct API need to fetch the status again"
                            else:
                                self.lhdn_invoice_status = 'submitted'
                                self.lhdn_documents_error = "May be The LHDN Take time to process your invoices, After some times need to fetch the status again"

                            self.lhdn_uuid = docUUID
                            self.lhdn_submission_uid = docSubmissionUID
                            self.message_post(body=_(
                                f"LHDN Direct API ==> Documents Submitted successfully", description=123))

                            # self.lhdn_json_data = json.loads(api_dict)
                            # if self.lhdn_invoice_status == 'validated':
                            #     self.send_validated_invoice_to_peppolsync_server(lhdn_setup_id)
                    else:
                        self.message_post(body=_('documents was rejected' + result.get('rejectedDocuments'),
                                                 description=123))
                        self.lhdn_documents_error = f"LHDN Direct API ==> Documents Rejected: ->{result.get('rejectedDocuments')}"
                        self.lhdn_invoice_status = 'error'
                else:
                    error = (str(result.get('rejectedDocuments'))) if result.get('rejectedDocuments') else str(
                        result.get('error'))
                    self.message_post(body=_('LHDN Direct API ==> Error Occured ==> ' + json.dumps(result),
                                             description=123))
                    self.lhdn_documents_error = f"LHDN Direct API ==> Errors Occured ==>{error}"
                    self.lhdn_invoice_status = 'error'

            else:
                self.lhdn_documents_error = f"LHDN Direct API ==> LHDN Access Token was not generated: ->{lhdn_token_generation.get('error') or lhdn_token_generation.get('message')}"
                self.lhdn_invoice_status = 'error'
                self.message_post(body=_(
                    f"LHDN Direct API ==> LHDN Access Token was not generated: ->{lhdn_token_generation.get('error') or lhdn_token_generation.get('message')}",
                    description=123))
        self._cr.commit()
        if use_peppol_documents_service and False:
            peppol_data_dict = {
                'client_id': lhdn_setup_id.peppol_sync_api_client_id,
                'client_password': lhdn_setup_id.peppol_sync_api_client_password,
                'senderId': self.company_id.partner_id.peppol_id,
                'receiverId': self.partner_id.peppol_id,
                'docTypeId': PEPPOL_DOCTYPE_ID[self.move_type],
                'processId': PEPPOL_PROCESS_ID[self.move_type],
                'xml_data': base64.b64decode(self.peppol_xml_attachment.datas).decode('utf-8')
            }

            headers = {'Content-Type': 'application/x-www-form-urlencoded'}
            peppol_res = requests.post(f"{lhdn_setup_id.peppol_sync_api_base_url}/v1/send_documents/peppol",
                                       params=peppol_data_dict,
                                       headers=headers)
            peppol_res = peppol_res.json()

            if peppol_res.get('status_code') == 200:
                self.is_sended_in_peppol = True
                self.message_post(
                    body=_("Peppol Network ==> Successfully Sended this invoices intos the Peppol Network",
                           description=123))
            else:
                self.is_sended_in_peppol = False
                self.message_post(
                    body=_(
                        f"Peppol Network ==> Documents sendings error ocuurings ins peppol ==> {peppol_res.get('error')}",
                        description=123))
            # else:

    def manually_documents_send_in_peppol_network(self):
        lhdn_setup_id = self.env['lhdn.setup'].search([], limit=1)
        if lhdn_setup_id.choose_submission_way == 'intermediate_api':
            if self.is_sended_in_peppol:
                raise UserError(_("This Documents is already sended ins via peppol Network"))
            # if not self.peppol_xml_attachment:
            #     raise UserError(_("Peppol XML Binary files fields data was not setted"))
            use_peppol_documents_service = False

            # xml_content_base64_string = self.peppol_xml_attachment.datas
            if self.partner_id.send_documents_via_peppol:
                if self.company_id.partner_id.peppol_status != 'registered':
                    raise UserError(
                        _(f"Need to Register Your company partner ({self.company_id.partner_id.name}) in Peppol SML; GO To Companyies -> click on the partner-> Enable the button Automatically Send Documents via Peppol?"))
                else:
                    use_peppol_documents_service = True
            if not self.partner_id.send_documents_via_peppol:
                raise UserError(
                    _(f"Needs to Enablings the Automatically Send Documents via Peppol? from the Customers ==> {self.partner_id.name}"))
            if use_peppol_documents_service:

                peppol_data_dict = {
                    'api_client_id': lhdn_setup_id.peppol_sync_api_client_id,
                    'api_client_password': lhdn_setup_id.peppol_sync_api_client_password,
                    'senderId': self.company_id.partner_id.peppol_id,
                    'receiverId': self.partner_id.peppol_id,
                    'docTypeId': PEPPOL_DOCTYPE_ID[self.move_type],
                    'processId': PEPPOL_PROCESS_ID[self.move_type],
                    'xml_data': False,
                    'inv_number': self.name
                    # base64.b64decode(xml_content_base64_string).decode('utf-8')
                }
                headers = {'Content-Type': 'application/x-www-form-urlencoded'}
                peppol_res = requests.post(f"{lhdn_setup_id.peppol_sync_api_base_url}/v1/send_documents/peppol",
                                           data=peppol_data_dict,
                                           headers=headers)
                # peppol_res = peppol_res.json()

                if peppol_res.status_code == 200:
                    self.is_sended_in_peppol = True
                    self.message_post(
                        body=_("Peppol Network ==> Successfully Sended this invoices intos the Peppol Network",
                               description=123))
                else:
                    self.is_sended_in_peppol = False
                    peppol_res = peppol_res.json()
                    self.message_post(
                        body=f"Peppol Network ==> Documents sendings error ocuurings ins peppol ==> {peppol_res.get('error')}")
                # else:
        else:
            if self.is_sended_in_peppol:
                raise UserError(_("This Documents is already sended ins via peppol Network"))
            if not self.peppol_xml_attachment:
                raise UserError(_("Peppol XML Binary files fields data was not setted"))
            use_peppol_documents_service = False

            xml_content_base64_string = self.peppol_xml_attachment.datas
            if self.partner_id.send_documents_via_peppol:
                if self.company_id.partner_id.peppol_status != 'registered':
                    raise UserError(
                        _(f"Need to Register Your company partner ({self.company_id.partner_id.name}) in Peppol SML; GO To Companyies -> click on the partner-> Enable the button Automatically Send Documents via Peppol?"))
                else:
                    use_peppol_documents_service = True
            if not self.partner_id.send_documents_via_peppol:
                raise UserError(
                    _(f"Needs to Enablings the Automatically Send Documents via Peppol? from the Customers ==> {self.partner_id.name}"))
            if use_peppol_documents_service:

                peppol_data_dict = {
                    'api_client_id': lhdn_setup_id.peppol_sync_api_client_id,
                    'api_client_password': lhdn_setup_id.peppol_sync_api_client_password,
                    'senderId': self.company_id.partner_id.peppol_id,
                    'receiverId': self.partner_id.peppol_id,
                    'docTypeId': PEPPOL_DOCTYPE_ID[self.move_type],
                    'processId': PEPPOL_PROCESS_ID[self.move_type],
                    'xml_data': base64.b64decode(xml_content_base64_string).decode('utf-8')
                }
                headers = {'Content-Type': 'application/x-www-form-urlencoded'}
                peppol_res = requests.post(f"{lhdn_setup_id.peppol_sync_api_base_url}/v1/send_documents/peppol",
                                           data=peppol_data_dict,
                                           headers=headers)
                # peppol_res = peppol_res.json()

                if peppol_res.status_code == 200:
                    self.is_sended_in_peppol = True
                    self.message_post(
                        body=_("Peppol Network ==> Successfully Sended this invoices intos the Peppol Network",
                               description=123))
                else:
                    self.is_sended_in_peppol = False
                    peppol_res = peppol_res.json()
                    self.message_post(
                        body=_(
                            f"Peppol Network ==> Documents sendings error ocuurings ins peppol ==> {peppol_res.get('error')}",
                            description=123))
                # else:

    def e_invoice_validate(self):
        if self.journal_id.not_required_e_invoice:
            raise UserError(_("This journal is not allowed to send in lhdn"))
        if (not self.lhdn_uuid) or (self.lhdn_invoice_status != 'validated'):
            if self.partner_id.tin_status == "invalid":
                raise UserError(
                    _("Needs to validating the Partner's TIN Number ==> Go to the Partners -> LHDN API Details"))
            if not self.partner_id.msic_code_id:
                raise UserError(_("Please Sets The MSIC Code into the Partner"))
            api_dict = self.lhdn_api_json_format_preparation()
            self.send_api_request(api_dict)
        else:
            return {
                'type': 'ir.actions.client',
                'tag': 'display_notification',
                'params': {
                    'type': 'success',
                    'message': _("This invoices document already Validated"),
                    'next': {'type': 'ir.actions.act_window_close'},
                }
            }
        # return True

    def self_billed_e_invoice(self):
        if not self.lhdn_uuid or (self.lhdn_invoice_status != 'validated'):
            api_dict = self.lhdn_api_json_format_preparation()
            self.send_api_request(api_dict)
        else:
            return {
                'type': 'ir.actions.client',
                'tag': 'display_notification',
                'params': {
                    'type': 'success',
                    'message': _("This invoices document already submitted"),
                    'next': {'type': 'ir.actions.act_window_close'},
                }
            }

    def cancel_e_invoice(self):
        if not self.lhdn_uuid:
            raise UserError(_("Documents not sended to the LHDN"))
        if not self.lhdn_document_cancellation_reason:
            raise UserError(_("Please add the LHDN document cancellation reason"))

        if not self.company_id.partner_id.tin:
            raise UserError(_("First need to set Company's related partners's TIN Number"))
        issuer_tin = self.company_id.partner_id.tin
        lhdn_setup_id = self.env['lhdn.setup'].search([], limit=1)
        # if lhdn_setup_id.choose_submission_way == 'intermediate_api':
        headers = {'Content-Type': 'application/json'}
        data = {
            'client_id': lhdn_setup_id.peppol_sync_api_client_id,
            'client_password': lhdn_setup_id.peppol_sync_api_client_password,
            # 'api_use': "myinvoice_api",
            'issuer_tin': issuer_tin,
            'uuid': self.lhdn_uuid,
            'cancel_reason': self.lhdn_document_cancellation_reason
            # 'peppol_credential': {},
            # 'myinvoice_credential': {'client_id': lhdn_setup_id.lhdn_api_client_id,
            #                          'client_secret': lhdn_setup_id.lhdn_api_client_password},
            # "invoice_dict": {'inv_number': self.name, 'cancel_reason': self.lhdn_document_cancellation_reason},
            # 'onbehalfof_tin': self.company_id.partner_id.tin
        }

        res = requests.post(f"{lhdn_setup_id.peppol_sync_api_base_url}/v1/cancel_document", params=json.dumps(data),
                            headers=headers)

        if res.status_code == 200:
            res = res.json()
            self.lhdn_invoice_status = "cancelled"
            self.message_post(body=_(
                f"LHDN Direct API ==> LHDN Documents Successfully Cancelled",
                description=123))
            self.button_cancel()
        else:
            errors_messageas = ""
            if res.text:
                # for error in res.get('error').get('details'):
                #     errors_messageas += error.get('message') + "\n"
                self.message_post(body=_(res.text, description=123))
                # self.button_cancel()
                return {
                    'type': 'ir.actions.client',
                    'tag': 'display_notification',
                    'params': {
                        'type': 'danger',
                        'message': _(res.text),
                        'next': {'type': 'ir.actions.act_window_close'},
                    }
                }
            # return True
        # else:
        #
        #     generated_token = self.lhdn_token_generation(lhdn_setup_id.lhdn_api_client_id,
        #                                                  lhdn_setup_id.lhdn_api_client_password, lhdn_setup_id)
        #     if generated_token.get('access_token'):
        #         access_token = generated_token.get('access_token')
        #         payload = json.dumps({
        #             "status": 'cancelled',
        #             "reason": self.lhdn_document_cancellation_reason,
        #         })
        #         headers = {
        #             'Content-Type': 'application/json',
        #             'Authorization': f'Bearer {access_token}'
        #         }
        #         lhdn_base_url = lhdn_setup_id.lhdn_sandbox_base_url if lhdn_setup_id.lhdn_connection_server_type == 'sandbox' else lhdn_setup_id.lhdn_production_base_url
        #
        #         get_documents_info = requests.get(lhdn_base_url + f'/api/v1.0/documents/{self.lhdn_uuid}/details',
        #                                           headers={'Authorization': f'Bearer {access_token}'}, data={})
        #         _logger.info(f"Gets documents Resultss ==> {get_documents_info.json()}")
        #         result = requests.put(lhdn_base_url + f'/api/v1.0/documents/state/{self.lhdn_uuid}/state',
        #                               headers=headers, data=payload)
        #         result = result.json()
        #         _logger.info(f"Cancellings results ===>{result}")
        #         if result.get('uuid'):
        #             self.lhdn_invoice_status = 'cancelled'
        #             self.message_post(body=_(
        #                 f"LHDN Direct API ==> LHDN Documents Successfully Cancelled",
        #                 description=123))
        #             self.button_cancel()
        #         else:
        #             self.lhdn_documents_error = f"LHDN Direct API ==> LHDN Error Ocuured ==>{str(result)}"
        #             self.message_post(
        #                 body=_(f"LHDN Direct API ==> LHDN Error Ocuured ==>{str(result)}", description=123))
        #
        #     else:
        #         self.lhdn_documents_error = f"LHDN Direct API ==> LHDN Access Token was not generated: ->{generated_token.get('access_token')}"
        #         self.message_post(body=_(
        #             f"LHDN Direct API ==> LHDN Access Token was not generated: ->{generated_token.get('access_token')}",
        #             description=123))

    def prepare_the_bills_from_raw_xml(self, root):
        # Define the namespaces to search with the correct prefixes
        namespaces = {
            'cbc': 'urn:oasis:names:specification:ubl:schema:xsd:CommonBasicComponents-2',
            'cac': 'urn:oasis:names:specification:ubl:schema:xsd:CommonAggregateComponents-2',
        }

        # Find the AccountingSupplierParty element
        accounting_supplier_party = root.find(".//cac:AccountingSupplierParty", namespaces)
        # Extract the TIN number
        tin_element = accounting_supplier_party.find(".//cac:PartyIdentification/cbc:ID[@schemeID='TIN']", namespaces)
        tin_number = tin_element.text
        # Extract the Registration Name
        registration_name_element = accounting_supplier_party.find(
            ".//cac:PartyLegalEntity/cbc:RegistrationName", namespaces)
        registration_name = registration_name_element.text
        # -------********
        vendor_id = self.env['res.partner'].search(
            ['|', ('name', 'ilike', registration_name), ('tin', '=', tin_number)], limit=1)

        if not vendor_id:
            raise UserError(
                _(f"This partner not found in the Systems database ==>{registration_name}, TIN==>{tin_number}"))

        # Extract Issue Date
        issue_date_element = root.find('cbc:IssueDate', namespaces)
        # -------********
        issue_date = issue_date_element.text if issue_date_element is not None else False

        # Extract Issue Time
        issue_time_element = root.find('cbc:IssueTime', namespaces)
        issue_time = issue_time_element.text if issue_time_element is not None else False

        # -------********
        issue_datetime_str = False
        # Combine Issue Date and Issue Time into a single datetime string in ISO 8601 format
        if issue_date != False and issue_time != False:
            # Convert to datetime object
            issue_datetime = datetime.strptime(f"{issue_date}T{issue_time}", "%Y-%m-%dT%H:%M:%SZ")
            # Format to Odoo compatible datetime string
            issue_datetime_str = issue_datetime.strftime("%Y-%m-%d %H:%M:%S")
        else:
            issue_datetime_str = False

        # Extract the Document Currency Code
        document_currency_code_element = root.find('cbc:DocumentCurrencyCode', namespaces)
        document_currency_code = document_currency_code_element.text if document_currency_code_element is not None else False

        # -------********
        currency_code_id = self.env['res.currency'].search(
            [('name', '=', document_currency_code)]) if document_currency_code else False

        # Iterate over each InvoiceLine element
        for invoice_line in root.findall('.//cac:InvoiceLine', namespaces):
            # Extract the required fields
            item_description = invoice_line.find('.//cac:Item/cbc:Description', namespaces).text
            invoiced_quantity = invoice_line.find('.//cbc:InvoicedQuantity', namespaces).text
            price_amount = invoice_line.find('.//cac:Price/cbc:PriceAmount', namespaces).text
            tax_category_percent = invoice_line.find('.//cac:TaxCategory/cbc:Percent', namespaces).text

            tax_id = self.env['account.tax'].search(
                [('amount', '=', float(tax_category_percent)), ('type_tax_use', '=', 'purchase')], limit=1)
            if not tax_id:
                raise UserError(_(f"Tax Percentages ==> {tax_category_percent}, not founds into the systems"))
            self.invoice_line_ids = [
                (0, 0, {
                    'name': item_description,
                    'quantity': invoiced_quantity,
                    'price_unit': price_amount,
                    'tax_ids': [(6, 0, [tax_id.id])]
                })
            ]

        self.partner_id = vendor_id.id
        self.invoice_date = issue_date
        self.invoice_issue_time = issue_datetime_str
        self.currency_id = currency_code_id.id

    def retrive_lhdn_invoice(self):
        if not self.lhdn_uuid:
            raise UserError(_("Fill the LHDN UUID Fields data"))
        find_duplicates_uuid_docs = self.env['account.move'].search(
            [('lhdn_uuid', '=', self.lhdn_uuid), ('id', '!=', self.id)])
        if find_duplicates_uuid_docs:
            raise UserError(
                f"This UUID==> {self.lhdn_uuid} ,already availables in this systems; Reference number ==> {find_duplicates_uuid_docs.name}")
        lhdn_setup_id = self.env['lhdn.setup'].search([], limit=1)
        lhdn_token_generation = self.lhdn_token_generation(lhdn_setup_id.lhdn_api_client_id,
                                                           lhdn_setup_id.lhdn_api_client_password, lhdn_setup_id)
        lhdn_base_url = lhdn_setup_id.lhdn_sandbox_base_url if lhdn_setup_id.lhdn_connection_server_type == 'sandbox' else lhdn_setup_id.lhdn_production_base_url

        if lhdn_token_generation.get('access_token'):
            access_token = lhdn_token_generation.get('access_token')
            get_documents_info = requests.get(
                lhdn_base_url + f'/api/v1.0/documents/{self.lhdn_uuid}/raw',
                headers={'Authorization': f'Bearer {access_token}'}, data={})
            documents_info = get_documents_info.json()
            if documents_info.get('document'):
                xml_document_raw = documents_info.get('document')

                # Parse the XML string
                root = ET.fromstring(xml_document_raw)
                self.prepare_the_bills_from_raw_xml(root)
                if documents_info.get('status') == "Invalid":
                    self.lhdn_invoice_status = 'submitted'
                elif documents_info.get('status') == "Valid":
                    self.lhdn_invoice_status = 'validated'
                elif documents_info.get('status') == "Cancelled":
                    self.lhdn_invoice_status = 'cancelled'
                else:
                    self.lhdn_invoice_status = 'error'

                self.is_created_from_lhdn_uuid = True
            else:
                raise UserError(f"Gettings an Errors ==> {documents_info}")
        else:
            raise UserError(f"Access token was not generated ==> {lhdn_token_generation}")

    def get_lhdn_documents_status(self):
        lhdn_setup_id = self.env['lhdn.setup'].search([], limit=1)

        lhdn_base_url = lhdn_setup_id.lhdn_sandbox_base_url if lhdn_setup_id.lhdn_connection_server_type == 'sandbox' else lhdn_setup_id.lhdn_production_base_url

        if lhdn_setup_id.choose_submission_way == 'intermediate_api':

            headers = {'Content-Type': 'application/json'}

            data = {
                'client_id': lhdn_setup_id.peppol_sync_api_client_id,
                'client_password': lhdn_setup_id.peppol_sync_api_client_password,
                'api_use': "myinvoice_api",
                'tin': '100000342',
                'peppol_credential': {},
                'myinvoice_credential': {},
                "invoice_dict": {'inv_number': self.name},
                'onbehalfof_tin': self.company_id.partner_id.tin
            }

            get_documents_info = requests.post(f'{lhdn_setup_id.peppol_sync_api_base_url}/v1/get_document_details',
                                               params=json.dumps(data),
                                               headers=headers)
            _logger.info(f'Gets Documents informations ==> {get_documents_info}')
            submitted_documents_info = get_documents_info.json()
            _logger.info(f'Gets Documents informations ==> {submitted_documents_info}')

            submitted_documents_info = submitted_documents_info.get('Result')
            # self.lhdn_longid = submitted_documents_info.get('longId')
            # self.lhdn_base_url = lhdn_base_url
            _logger.info(f'Gets Documents informations ==> {submitted_documents_info}')
            if submitted_documents_info:
                if submitted_documents_info.get('status') == 'Invalid':
                    is_duplicated_error = False
                    for err in submitted_documents_info.get('validationResults').get('validationSteps'):
                        if err.get('name') == "Step03-Duplicated Submission Validator":
                            is_duplicated_error = True
                    if is_duplicated_error:
                        self.lhdn_invoice_status = 'error'
                        self.lhdn_uuid = False
                        self.lhdn_submission_uid = False
                        self.lhdn_documents_error = "Submitted documents again"
                    else:
                        self.lhdn_invoice_status = 'submitted'
                    self.message_post(body=_(
                        f"LHDN Direct API ==> Documents Invalides Reason {submitted_documents_info}",
                        description=123))
                    self.lhdn_documents_error = "Submitted Documents was an Invalid,Please refere the Chatter"
                elif submitted_documents_info.get('status') == 'Valid':
                    self.lhdn_invoice_status = 'validated'
                    if not self.lhdn_longid:
                        self.lhdn_longid = submitted_documents_info.get('longId')
                    self.lhdn_documents_error = ""

                elif submitted_documents_info.get('status') == 'Submitted':
                    self.message_post(body=_(
                        f"LHDN Direct API ==> Documentss Gettings errors ==> {submitted_documents_info}",
                        description=123))
                    # Because of too lates response from the lhdn regardings the updatings the Valid status
                    self.lhdn_invoice_status = 'submitted'
                    self.lhdn_documents_error = "May be The Late Response from the LHDN Direct API need to fetch the status again"
                else:
                    self.lhdn_invoice_status = 'submitted'
                    self.lhdn_documents_error = "May be The LHDN Take time to process your invoices, After some times need to fetch the status again"

                # self.lhdn_uuid = submitted_documents_info.get('uuid')  # docUUID
                # self.lhdn_submission_uid = submitted_documents_info.get('submissionUid')  # docSubmissionUID
                # self.message_post(body=_(
                #     f"LHDN Intermediates API ==> Documents Submitted successfully", description=123))

                # self.lhdn_invoice_status = 'validated'
                # lhdn_doc_dict = res.get('myinvoice_result').get('myinvoice_result')[0]
                # self.lhdn_uuid = lhdn_doc_dict['docUUID']
                # self.lhdn_submission_uid = lhdn_doc_dict['docSubmissionUID']
                self.lhdn_documents_error = ""
            else:
                self.lhdn_documents_error = "May be The LHDN Take time to process your invoices, After some times need to fetch the status again"
                self.lhdn_invoice_status = 'submitted'

            # raise UserError(_("For the PeppolSync(Intermediate API) need to implimetings this code"))
        else:
            lhdn_token_generation = self.lhdn_token_generation(lhdn_setup_id.lhdn_api_client_id,
                                                               lhdn_setup_id.lhdn_api_client_password, lhdn_setup_id)
            if lhdn_token_generation.get('access_token'):
                access_token = lhdn_token_generation.get('access_token')

                get_documents_info = requests.get(
                    lhdn_base_url + f'/api/v1.0/documents/{self.lhdn_uuid}/details',
                    headers={'Authorization': f'Bearer {access_token}'}, data={})
                submitted_documents_info = get_documents_info.json()

                self.lhdn_longid = submitted_documents_info.get('longId')

                _logger.info(f'Gets Documents informations ==> {submitted_documents_info}')
                if submitted_documents_info.get('status') == 'Invalid':
                    self.lhdn_invoice_status = 'submitted'
                    self.message_post(body=_(
                        f"LHDN Direct API ==> Documents Invalides Reason {submitted_documents_info}",
                        description=123))
                    self.lhdn_documents_error = "Submitted Documetns was an Invalid Please refere the Chatter"
                elif submitted_documents_info.get('status') == 'Valid':
                    self.lhdn_invoice_status = 'validated'
                    self.lhdn_documents_error = ""
                    # self.send_validated_invoice_to_peppolsync_server(lhdn_setup_id)
                else:
                    self.message_post(body=_(
                        f"LHDN Direct API ==> Documentss Gettings errors ==> {submitted_documents_info}",
                        description=123))
                    # Because of too lates response from the lhdn regardings the updatings the Valid status
                    self.lhdn_invoice_status = 'submitted'
                    self.lhdn_documents_error = "May be The Late Response from the LHDN Direct API need to fetch the status again"
            else:
                raise UserError(_(f"Errors Ocuringa durings The Access Tokens Generation==> {lhdn_token_generation}"))

    def matching_lhdn_invoice(self):
        if not self.lhdn_uuid:
            raise UserError(_("Fill the LHDN UUID Fields data"))
        find_duplicates_uuid_docs = self.env['account.move'].search(
            [('lhdn_uuid', '=', self.lhdn_uuid), ('id', '!=', self.id)])
        if find_duplicates_uuid_docs:
            raise UserError(
                f"This UUID==> {self.lhdn_uuid} ,already availables in this systems; Reference number ==> {find_duplicates_uuid_docs.name}")
        lhdn_setup_id = self.env['lhdn.setup'].search([], limit=1)
        lhdn_token_generation = self.lhdn_token_generation(lhdn_setup_id.lhdn_api_client_id,
                                                           lhdn_setup_id.lhdn_api_client_password, lhdn_setup_id)
        lhdn_base_url = lhdn_setup_id.lhdn_sandbox_base_url if lhdn_setup_id.lhdn_connection_server_type == 'sandbox' else lhdn_setup_id.lhdn_production_base_url

        if lhdn_token_generation.get('access_token'):
            access_token = lhdn_token_generation.get('access_token')
            get_documents_info = requests.get(
                lhdn_base_url + f'/api/v1.0/documents/{self.lhdn_uuid}/raw',
                headers={'Authorization': f'Bearer {access_token}'}, data={})
            documents_info = get_documents_info.json()
            if documents_info.get('document'):
                receiver_tin = documents_info.get('receiverId')
                total_amount = documents_info.get('totalPayableAmount')
                if self.partner_id.tin == receiver_tin and self.amount_total == total_amount:
                    self.ref = documents_info.get('internalId')
                    self.lhdn_submission_uid = documents_info.get('submissionUid')
                    if documents_info.get('status') == 'Submitted':
                        self.lhdn_invoice_status = 'submitted'
                    elif documents_info.get('status') == 'Invalid':
                        self.lhdn_invoice_status = 'invalid'
                    elif documents_info.get('status') == 'Valid':
                        self.lhdn_invoice_status = 'validated'
                    else:
                        self.lhdn_invoice_status = 'error'
                else:
                    self.lhdn_uuid = ""
                    raise UserError(_("Invoices is not matched with the given LHDN UUID"))
            else:
                raise UserError(f"Gettings an Errors ==> {documents_info}")
        else:
            raise UserError("Access token was not generatids")

    def rejection_requests_lhdn_invoice(self):
        if not self.lhdn_document_cancellation_reason:
            raise UserError(_("Fill the Cancellations / Rejections Fields data"))
        # if not self.lhdn_uuid:
        #     raise UserError(_("Fill the LHDN UUID Fields data"))
        # find_duplicates_uuid_docs = self.env['account.move'].search(
        #     [('lhdn_uuid', '=', self.lhdn_uuid), ('id', '!=', self.id)])
        # if find_duplicates_uuid_docs:
        #     raise UserError(
        #         f"This UUID==> {self.lhdn_uuid} ,already availables in this systems; Reference number ==> {find_duplicates_uuid_docs.name}")
        lhdn_setup_id = self.env['lhdn.setup'].search([], limit=1)
        lhdn_token_generation = self.lhdn_token_generation(lhdn_setup_id.lhdn_api_client_id,
                                                           lhdn_setup_id.lhdn_api_client_password, lhdn_setup_id)
        lhdn_base_url = lhdn_setup_id.lhdn_sandbox_base_url if lhdn_setup_id.lhdn_connection_server_type == 'sandbox' else lhdn_setup_id.lhdn_production_base_url

        if lhdn_token_generation.get('access_token'):
            access_token = lhdn_token_generation.get('access_token')

            payload = json.dumps({
                "status": "rejected",
                "reason": self.lhdn_document_cancellation_reason
            })
            headers = {
                'Content-Type': 'application/json',
                'Authorization': f'Bearer {access_token}'
            }

            get_documents_info = requests.put(
                lhdn_base_url + f'/api/v1.0/documents/state/{self.lhdn_uuid}/state',
                headers=headers, data=payload)
            documents_info = get_documents_info.json()
            if documents_info.get('status'):
                if documents_info.get('status') == 'Rejected':
                    self.lhdn_invoice_status = 'rejected'
                    self.message_post(body=_(
                        f"LHDN Direct API ==> Documents Rejected request successfully", description=123))
            else:
                raise UserError(f"Gettings an Errors ==> {documents_info}")
        else:
            raise UserError("Access token was not generatids")

    def action_cron_processings_an_portal_ai_invoice(self):
        lhdn_setup_id = self.env['lhdn.setup'].search([], limit=1)
        # portal_inv_store_path = '/Users/onlymac/workspace/odoo_v17/custom_addons/portal_inv'
        portal_inv_store_path = '/home/ubuntu/portal_inv'
        todays_inv_path = portal_inv_store_path + '/' + datetime.now().date().strftime("%d_%m_%Y")
        todays_completed_dir_path = todays_inv_path + '/' + 'completed'
        todays_not_completed_dir_path = todays_inv_path + '/' + 'not_completed'

        if os.path.exists(todays_not_completed_dir_path):
            # List all files in the directory
            all_files = os.listdir(todays_not_completed_dir_path)
            # Filter out non-PDF files
            pdf_files = [f for f in all_files if f.lower().endswith('.pdf')]
            if pdf_files:
                selected_pdf_files = pdf_files[:2]
                for file in selected_pdf_files:
                    _logger.info(f"files==>{file} started")
                    current_file_path = todays_not_completed_dir_path + '/' + file
                    files = [('file', (file, open(current_file_path, 'rb'), 'application/pdf'))]
                    url = 'http://103.76.88.17:5000/analyze_invoice'
                    response = requests.post(url, files=files)
                    if response.status_code == 200:
                        lhdn_setup_id.peppol_credit -= 2
                        print("File analyzed successfully")
                        xml_inv_text = response.text
                        _logger.info(f"LHDN PDFs toeas XML ==>{xml_inv_text}")
                        xml_inv_text = re.sub(r'&(?!amp;)', '&amp;', xml_inv_text)
                        # | lt; | gt; | quot; | apos;

                        # Parse the XML response
                        tree = ET.fromstring(xml_inv_text)

                        # Extract invoice type code
                        namespace = {
                            'inv': "urn:oasis:names:specification:ubl:schema:xsd:Invoice-2",
                            'cac': "urn:oasis:names:specification:ubl:schema:xsd:CommonAggregateComponents-2",
                            'cbc': "urn:oasis:names:specification:ubl:schema:xsd:CommonBasicComponents-2"
                        }
                        invoice_type_code = tree.find('cbc:InvoiceTypeCode', namespace).text

                        invoices_ref_number = tree.find('cbc:ID', namespace).text

                        # Extract customer details
                        customer_data = tree.find('cac:AccountingCustomerParty/cac:Party', namespace)
                        customer_name = customer_data.find('cac:PartyLegalEntity/cbc:RegistrationName', namespace).text
                        # customer_brn = customer_data.find('cac:PartyIdentification[cbc:ID[@schemeID="BRN"]]/cbc:ID',
                        #                                   namespace).text
                        customer_tin = tree.find(
                            './/cac:AccountingCustomerParty/cac:Party/cac:PartyIdentification/cbc:ID[@schemeID="TIN"]',
                            namespace)
                        if customer_tin:
                            customer_tin = customer_tin.text
                        else:
                            customer_tin = "N/A"
                        customer_brn = tree.find(
                            './/cac:AccountingCustomerParty/cac:Party/cac:PartyIdentification/cbc:ID[@schemeID="BRN"]',
                            namespace)
                        # if customer_brn.text:
                        if customer_brn == None:
                            customer_brn = False
                        else:
                            customer_brn = customer_brn.text or False
                        # else:
                        # customer_brn = "N/A"

                        # Extract invoice lines
                        invoice_lines = tree.findall('cac:InvoiceLine', namespace)
                        line_data = []
                        for line in invoice_lines:
                            description = line.find('cac:Item/cbc:Description', namespace).text
                            quantity = line.find('cbc:InvoicedQuantity', namespace).text
                            price = line.find('cac:Price/cbc:PriceAmount', namespace).text
                            tax_amount = line.find('cac:TaxTotal/cbc:TaxAmount', namespace)
                            if quantity:
                                digits = re.findall(r'\d+\.\d+|\d+', quantity)
                                quantity = ''.join(digits)
                            total_line_excl_tax = float(quantity) * float(price)
                            if tax_amount != None and tax_amount.text:
                                tax_amount = float(tax_amount.text)
                            else:
                                tax_amount = 0
                            tax_rate = 0
                            if tax_amount:
                                tax_rate = ceil(round((tax_amount / total_line_excl_tax) * 100, 2))
                            line_data.append({
                                'description': description,
                                'quantity': float(quantity),
                                'price': float(price),
                                'tax_rate': tax_rate,
                            })

                        # Create or get customer
                        customer = False
                        if customer_name and customer_name != None:
                            customer = self.env['res.partner'].sudo().search([('name', '=', customer_name)], limit=1)
                            if not customer:
                                customer = self.env['res.partner'].sudo().create(
                                    {'name': customer_name, 'tin_status': 'validated', 'tin': customer_tin})
                                if customer_brn and customer_brn != 'N/A':
                                    customer.update({'brn': customer_brn, 'send_documents_via_peppol': True})
                                customer.msic_code_id = self.env['lhdn.msic.code'].sudo().search([], limit=1).id
                        # Map the invoice type code to an appropriate Odoo type
                        invoice_type_mapping = {
                            '01': 'out_invoice',
                            "02": 'out_refund',
                            "11": 'in_invoice',
                            "12": 'in_refund'
                            # Add other mappings as needed
                        }
                        move_type = invoice_type_mapping.get(invoice_type_code, 'out_invoice')

                        # Create the invoice
                        invoice_vals = {
                            'partner_id': customer.id if customer else False,
                            'move_type': move_type,
                            'invoice_line_ids': [],
                            'portal_ai_inv_number': invoices_ref_number,
                            'company_id': self.env.company.id,
                        }
                        for line in line_data:
                            product = self.env['product.product'].sudo().search([('name', '=', line['description'])],
                                                                                limit=1)
                            if not product:
                                product = self.env['product.product'].sudo().create({'name': line['description']})
                            tax_id = self.env['account.tax'].search(
                                [('amount', '=', line['tax_rate']), ('type_tax_use', '=', 'sale'),
                                 ('company_id', '=', self.env.company.id)], limit=1)
                            if not tax_id:
                                tax_group_id = self.env['account.tax.group'].sudo().search(
                                    [('name', '=', str(line['tax_rate'])), ('company_id', '=', self.env.company.id)],
                                    limit=1)
                                if not tax_group_id:
                                    tax_group_id = self.env['account.tax.group'].create({
                                        'name': str(line['tax_rate']),  # SST oreas GST
                                        'company_id': self.env.company.id,
                                    })
                                tax_id = self.env['account.tax'].sudo().create(
                                    {'name': line['tax_rate'], 'amount': line['tax_rate'], 'type_tax_use': 'sale',
                                     'invoice_label': line['tax_rate'], 'tax_group_id': tax_group_id.id})
                            invoice_vals['invoice_line_ids'].append((0, 0, {
                                'product_id': product.id,
                                'quantity': line['quantity'],
                                'price_unit': line['price'],
                                'name': line['description'],
                                'tax_ids': [tax_id.id]
                            }))
                            if not product.lhdn_classification_id:
                                product.lhdn_classification_id = self.env[
                                    'lhdn.item.classification.code'].sudo().search(
                                    [], limit=1).id

                        inv = self.env['account.move'].sudo().create(invoice_vals)
                        inv.invoice_issue_time = datetime.now() - timedelta(hours=6)
                        inv.invoice_date = datetime.now()
                        inv.is_created_from_ai = True

                        _logger.info(f"files==>{file} Completeds, invocieas names ==> {inv.name}")

                        # inv.e_invoice_validate()
                        # Moves the Sucessfullys compleetedings filweas toeas completeds fileas directoryieas
                        source_file_path = os.path.join(todays_not_completed_dir_path, file)
                        target_file_path = os.path.join(todays_completed_dir_path, file)

                        self._cr.commit()

                        shutil.move(source_file_path, target_file_path)

                    else:
                        raise UserError("File analysis failed")

    def action_cron_processings_get_notifications(self):
        lhdn_setup_id = self.env['lhdn.setup'].search([], limit=1)
        lhdn_token_generation = self.lhdn_token_generation(lhdn_setup_id.lhdn_api_client_id,
                                                           lhdn_setup_id.lhdn_api_client_password, lhdn_setup_id)
        lhdn_base_url = lhdn_setup_id.lhdn_sandbox_base_url if lhdn_setup_id.lhdn_connection_server_type == 'sandbox' else lhdn_setup_id.lhdn_production_base_url

        if lhdn_token_generation.get('access_token'):
            access_token = lhdn_token_generation.get('access_token')

            payload = json.dumps({
                "status": "rejected",
                "reason": self.lhdn_document_cancellation_reason
            })
            headers = {
                'Content-Type': 'application/json',
                'Authorization': f'Bearer {access_token}'
            }
            todays_date = datetime.now().date()
            query = f"dateFrom={todays_date.strftime('%Y-%m-%d')}&dateTo={todays_date.strftime('%Y-%m-%d')}&pageNo=1&pageSize=50"
            get_documents_info = requests.get(
                lhdn_base_url + f'/api/v1.0/notifications/taxpayer?{query}',
                headers=headers, data=payload)
            documents_info = get_documents_info.json()

    def action_send_batch_for_e_invoice_validate(self):
        for rec in self:
            if rec.state == "posted" and rec.lhdn_invoice_status in ["new", "error"]:
                rec.e_invoice_validate()

    def action_combine_multiple_invoice_to_one_invoice(self):
        find_general_public_partner = self.env['res.partner'].search([('name', '=', 'general public')], limit=1)
        if not find_general_public_partner:
            raise UserError(_("general public partner not found ins your system"))
        new_inv = self.env['account.move'].create({
            'partner_id': find_general_public_partner.id,
            'invoice_date': datetime.now().date(),
            'move_type': 'out_invoice'
        })
        combined_inv_list = []
        for rec in self:
            if rec.partner_id.id == find_general_public_partner.id and rec.lhdn_invoice_status == "new":
                for line in rec.invoice_line_ids:
                    line.copy({
                        'older_invoice_line_id': line.id,
                        'move_id': new_inv.id
                    })
                rec.state = 'draft'
                combined_inv_list.append(rec.name)
        new_inv.message_post(body=f"This invoice are combine from the ==> {combined_inv_list}")

    def action_reverse_refund_note(self):
        action = self.env["ir.actions.actions"]._for_xml_id("account.action_view_account_move_reversal")

        # if self.is_invoice():
        action['name'] = _('Refund Note')

        return action

    def action_reverse_debit_note(self):
        action = self.env["ir.actions.actions"]._for_xml_id("account.action_view_account_move_reversal")

        # if self.is_invoice():
        action['name'] = _('Debit Note')

        return action
