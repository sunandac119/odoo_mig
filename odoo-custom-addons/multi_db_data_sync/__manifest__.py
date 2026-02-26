# -*- coding: utf-8 -*-
{
    'name': "Multi Database Data Synchronisation",

    'summary': """
        Two-database sync module
        """,

    'description': """
        Automatically transfers and updates records between two Odoo databases using secure synchronization processes.
    """,

    'author': "Acespritech",
    'website': "",

    # Categories can be used to filter modules in modules listing
    # Check https://github.com/odoo/odoo/blob/14.0/odoo/addons/base/data/ir_module_category_data.xml
    # for the full list
    'category': 'POS',
    'version': '0.1',

    # any module necessary for this one to work correctly
    'depends': ['base','uom_barcode_scanner', 'product_data_transfer'],

    # always loaded
    'data': [
        'views/res_config_setting_view.xml',
        'data/ir_cron.xml', 
    ],
}
