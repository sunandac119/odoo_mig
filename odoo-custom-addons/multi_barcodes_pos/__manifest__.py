# -*- coding: utf-8 -*-

{
    'name': 'POS Product Multi Barcode',
    'summary': 'Allows multiple barcodes for a single product',
    'description': 'Allows multiple barcodes for a single product',
    'version': '14.0.1.0.2',
    'author': 'Cybrosys Techno Solutions',
    'company': 'Cybrosys Techno Solutions',
    'website': 'https://www.cybrosys.com/',
    'category': 'Point of Sale',
    'depends': ['product', 'point_of_sale'],
    'license': 'AGPL-3',

    'data': [
        'security/ir.model.access.csv',
        'views/product_views.xml',
        # ⚠️ see ISSUE 2 below
    ],

    'assets': {
        'point_of_sale.assets': [
            'multi_barcodes_pos/static/src/js/*.js',
        ],
    },

    'images': ['static/description/banner.png'],
    'installable': True,
    'auto_install': False,
}
