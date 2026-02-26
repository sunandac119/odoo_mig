# -*- coding: utf-8 -*-
{
    'name': "Omni Print: Direct Print from Desktop",
    'summary': """Directly print your Odoo document(Sale Order, Invoice, Product Label etc) with a single click.""",
    'version': '1.0.3',
    'author': "Omni Byte",
    'website': "https://omni-byte.com/",
    'images': ['static/description/main_screenshot.png'],
    'support': "support@omni-byte.com",
    'live_test_url': 'https://demo.omni-byte.com/',
    'license': "OPL-1",
    'category': 'Printer',
    'price': 0,
    'currency': 'EUR',
    'depends': ['base', 'web'],
    'data': [
        'views/views.xml',
        'views/assets.xml',
        'data/config_data.xml',
    ],
    'qweb': [
        'static/src/xml/systray.xml'
    ],
    'application': True,
}
