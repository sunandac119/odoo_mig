# -*- coding: utf-8 -*-
# This module and its content is copyright of Technaureus Info Solutions Pvt. Ltd.
# - © Technaureus Info Solutions Pvt. Ltd 2020. All rights reserved.

{
    'name': 'Inventory Adjustments With Barcode',
    'version': '14.0.0.1',
    'sequence': 1,
    'category': 'Operations/Inventory',
    'summary': 'Stock Checking by using barcode scanner',
    'description': """
    Stock Checking or Inventory Adjustments With Barcode Scanner
""",
    'author': 'Technaureus Info Solutions Pvt. Ltd.',
    'website': 'http://www.technaureus.com/',
    'license': 'Other proprietary',
    'price': 9,
    'currency': 'EUR',
    'depends': ['stock', 'barcodes'],
    'data': [
        'security/ir.model.access.csv',
        'wizard/stock_check_wizard_views.xml',
        'views/stock_inventory_views.xml',
    ],
    'demo': [],
    'images': ['images/main_screenshot.png'],
    'installable': True,
    'auto_install': False,
    'application': True,
    'live_test_url': 'https://www.youtube.com/watch?v=DrNz8aXkBN8&t=140s'
}
