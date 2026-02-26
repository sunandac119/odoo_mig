# -*- coding: utf-8 -*-
{
    'name': "UoM Barcodes",

    'summary': """
        Adding multi UoMs and barcodes in POS products
        """,

    'description': """
    using sub-barcodes in the POS scanner instead of the default product barcode
    """,

    'author': "Acespritech",
    'website': "",

    # Categories can be used to filter modules in modules listing
    # Check https://github.com/odoo/odoo/blob/14.0/odoo/addons/base/data/ir_module_category_data.xml
    # for the full list
    'category': 'POS',
    'version': '0.1',

    # any module necessary for this one to work correctly
    'depends': ['base','product', 'sale', 'purchase', 'purchase_stock', 'stock','mrp', 'wedo_sale_return', 'wedo_purchase_return_managment', 'warehouse_stock_request_app', 'order_report', 'product_pricelist_packaging_knk'],

    # always loaded
    'data': [
        'security/ir.model.access.csv',
        # 'data/schedule_action.xml',
        'views/assets_backend.xml',
        'views/products.xml',
        'views/pricelist_barcode.xml',
        'views/sale_order.xml',
        'views/stock_picking_view.xml',
        'views/mrp_production_view.xml',
        'views/mrp_bom_view.xml',
        'views/purchase_order_view.xml',
        'views/sale_return.xml',
        'views/purchase_return.xml',
        'views/studio_changes.xml',
        'views/res_company_view.xml',
        'views/account_move_line.xml',
        'report/print_barcode_report.xml',
        'report/print_barcode_template.xml',
        'report/account_move_report.xml',
        'wizard/pricelist_import_wizard_view.xml',
    ],
}
