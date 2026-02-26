# -*- coding: utf-8 -*-
{
    'name': "Product Label",

    'summary': """Product Label printing functionality as v15.""",

    'description': """
        This module adds Product Label printing functionality as v15.
    """,

    'author': "Bista Solutions Pvt. Ltd.",
    'website': "https://www.bistasolutions.com",

    # Categories can be used to filter modules in modules listing
    # Check https://github.com/odoo/odoo/blob/13.0/odoo/addons/base/data/ir_module_category_data.xml
    # for the full list
    'category': 'Operations/Inventory',
    'version': '14.0.1.0.2',

    'application': True,

    # any module necessary for this one to work correctly
    'depends': ['base', 'stock', 'product', 'product_expiry', 'stock_picking_batch'],

    # always loaded
    'data': [
        'security/ir.model.access.csv',
        'views/res_config_settings_views.xml',
        'wizard/product_label_layout_views.xml',
        'report/product_reports.xml',
        'report/product_product_templates.xml',
        'report/product_template_templates.xml',
        'views/product_views.xml',
        'views/stock_picking_views.xml',
        'report/picking_templates.xml',
        'report/report_stockpicking_operations.xml',
        'report/report_picking_batch.xml',
    ],
}
