# -*- coding: utf-8 -*-
# Part of Browseinfo. See LICENSE file for full copyright and licensing details.
{
    'name': 'Account Payment-Voucher Double Approval Workflow',
    'version': '14.0.0.2',
    'category': 'Account',
    'sequence': 15,
    'summary': 'payment double approve payment Double Validation Approval voucher double approval process voucher double validation account payment approval workflow voucher approval process payment triple approval voucher triple validate account payment manager approval',
    'description': """
        This app helps you to double approval process for Payment/Voucher.
    odoo Payment double validation Workflow Voucher Double validation Workflow
    odoo payment double approval voucher double approval
    odoo payment approval validation payment double validation voucher validation
    odoo double validate payment double validation on voucher approval workflow on voucher
    odoo Validation process on payment voucher Double validation on payment Confirm payment approval
    odoo Confirm voucher approval multiple payment approval multiple voucher approval
    odoo multiple approval for payment multiple approval for voucher

    odoo Account Payment double validation Workflow Account Voucher Double validation Workflow
    odoo Account payment double approval Account voucher double approval
    odoo Account payment approval validation Account payment double validation Account voucher validation
    odoo double validate Account payment double validation on Account voucher approval workflow on Account voucher
    odoo Validation process on Account payment Account voucher Double validation on Account payment Confirm Account payment approval
    odoo Confirm Account voucher approval multiple Account payment approval multiple Account voucher approval
    odoo multiple approval for Account payment multiple approval for Account voucher odoo


    odoo Accounting Payment double validation Workflow Accounting Voucher Double validation Workflow
    odoo Accounting payment double approval Accounting voucher double approval
    odoo Accounting payment approval validation Accounting payment double validation Accounting voucher validation
    odoo double validate Accounting payment double validation on Accounting voucher approval workflow on Accounting voucher
    odoo Validation process on Accounting payment Accounting voucher Double validation on Accounting payment Confirm Accounting payment approval
    odoo Confirm Accounting voucher approval multiple Accounting payment approval multiple Accounting voucher approval
    odoo multiple approval for Accounting payment multiple approval for Accounting voucher odoo



    """,
    'website': 'https://www.browseinfo.com',
    'price': 15,
    'currency': "EUR",
    'author': 'BrowseInfo',
    'depends': ['base','account'],
    'data': [
            'security/ir.model.access.csv',
            'security/account_payment_groups.xml',
            'data/account_payment_config_data.xml',
            'views/res_config_settings_views.xml',
            'views/account_payment_view.xml',
            # 'views/account_voucher_view.xml',
            ],
    'demo': [],
    'css': [],
    'installable': True,
    'auto_install': False,
    'application': True,
    'live_test_url':'https://youtu.be/OWLYVChNADs',
    "images":['static/description/Banner.png'],
}
