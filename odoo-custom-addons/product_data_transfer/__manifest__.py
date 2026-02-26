# -*- coding: utf-8 -*-
{
    'name': "Product Data Transfer",

    'summary': """
        """,

    'description': """
    """,

    'author': "Acespritech",
    'website': "",

    # Categories can be used to filter modules in modules listing
    # Check https://github.com/odoo/odoo/blob/14.0/odoo/addons/base/data/ir_module_category_data.xml
    # for the full list
    'category': 'Product',
    'version': '0.1',

    # any module necessary for this one to work correctly
    'depends': ['base','product', 'pos_multi_uom_barcode', 'stock'],

    # always loaded
    'data': [
        'security/ir.model.access.csv',
        'data/server_action.xml',
        'data/ir_cron.xml',
        'views/product_uom_mismatch_action.xml',
        'wizard/vendor_product_export_wizard_view.xml',
    ],
}
