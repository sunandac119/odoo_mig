# -*- coding: utf-8 -*-
{
    'name': "Automatic old data cleanup",

    'summary': """
        Automatic old data cleanup
        """,

    'description': """
       Automatically deletes records older than thirteen months, improving database performance, reducing storage usage, and maintaining system efficiency.
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
        'data/ir_cron.xml', 
    ],
}
