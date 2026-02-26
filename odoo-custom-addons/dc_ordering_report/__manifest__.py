# -*- coding: utf-8 -*-
{
    'name': "DC order report",

    'summary': """
        DC order report
        """,

    'description': """
        DC order report
    """,

    'author': "Acespritech",
    'website': "",

    # Categories can be used to filter modules in modules listing
    # Check https://github.com/odoo/odoo/blob/14.0/odoo/addons/base/data/ir_module_category_data.xml
    # for the full list
    'category': 'POS',
    'version': '0.1',

    # any module necessary for this one to work correctly
    'depends': ['base', 'order_report'],

    # always loaded
    'data': [
        'wizard/wizard_inventory_valuation.xml',
    ],
}
