# -*- coding: utf-8 -*-
{
    'name': "Product Barcodes",

    'summary': """
        Adding multi UoMs and barcodes in products for sale order line
        """,
    'category': 'Sale',
    'version': '14.1',

    'depends': ['base', 'sale'],

    'data': [
        'views/sale_order_line_view.xml',
    ],
}
