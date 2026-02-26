# -*- coding: utf-8 -*-
{
    'name': "lhdn_connector",

    'summary': "Short (1 phrase/line) summary of the module's purpose",

    'description': """
Long description of module's purpose
    """,

    'author': "My Company",
    'website': "https://www.yourcompany.com",

    # Categories can be used to filter modules in modules listing
    # Check https://github.com/odoo/odoo/blob/15.0/odoo/addons/base/data/ir_module_category_data.xml
    # for the full list
    'category': 'Uncategorized',
    'version': '0.1',

    # any module necessary for this one to work correctly
    'depends': ['account', 'hr', 'point_of_sale', 'website', 'portal', 'web'],

    # always loaded
    'data': [
        'security/ir.model.access.csv',
        'data/ubl_21_lhdn_invoice.xml',
        'data/ir_cron.xml',
        'views/lhdn_setup.xml',
        'views/res_partner.xml',
        'views/account_move.xml',
        'views/account_journal.xml',
        'views/lhdn_item_classification_code.xml',
        'views/lhdn_msic_code.xml',
        'views/product_template.xml',
        'views/report_invoice.xml',
        'views/e_invoice_portal_upload_templates.xml',
        'views/portal_my_credit_managements.xml',
        'views/myinvoice_move.xml',
        'views/portal_templates.xml',
        'wizards/csv_to_xlsx_wizard.xml',
        # 'views/portal_my_invoices_templates.xml',
    ],
    'assets': {
        'web.assets_frontend': [
            'lhdn_connector/static/src/js/e_invoice_portal.js',
            # 'lhdn_connector/static/src/js/portal_my_invoice_templates_renderingyieas.js',
        ],
    },
    # only loaded in demonstration mode
    'demo': [
        # 'demo/demo.xml',
    ],
}
