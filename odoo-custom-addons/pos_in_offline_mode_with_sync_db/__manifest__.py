# -*- coding: utf-8 -*-
{
    'name': "pos_in_offline_mode_with_sync_db",

    'summary': """
        Short (1 phrase/line) summary of the module's purpose, used as
        subtitle on modules listing or apps.openerp.com""",

    'description': """
        Long description of module's purpose
    """,

    'author': "My Company",
    'website': "http://www.yourcompany.com",

    # Categories can be used to filter modules in modules listing
    # Check https://github.com/odoo/odoo/blob/14.0/odoo/addons/base/data/ir_module_category_data.xml
    # for the full list
    'category': 'Uncategorized',
    'version': '3.0.1',

    # any module necessary for this one to work correctly
    'depends': ['point_of_sale', 'sale_management', 'stock', 'account', 'crm', 'product', 'hr', 'multi_barcodes_pos',
                'sale_pos_multi_barcodes_app'],

    # always loaded
    'data': [
        # 'security/ir.model.access.csv',
        # 'views/views.xml',
        # 'views/templates.xml',
        'data/data.xml',
        'views/pos_order.xml',
        'views/pos_sessions.xml',
        'views/pos_payments.xml',
        'views/res_config_settings_views.xml',
        # 'views/pos_config.xml',
    ],
    # only loaded in demonstration mode
    'demo': [
        # 'demo/demo.xml',
    ],
    # 'uninstall_hook': 'uninstall_hook',  # Calls the uninstall_hook method
}
