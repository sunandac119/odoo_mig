# -*- coding: utf-8 -*-
{
    'name': 'POS Disable Price Mode',
    'version': '14.0.1.0.0',
    'category': 'Point of Sale',
    'summary': 'Disable the Price button/mode for all POS users',
    'author': 'ChatGPT',
    'license': 'LGPL-3',
    'depends': ['point_of_sale'],
    'data': [],
    'qweb': [],
    'assets': {
        'point_of_sale.assets': [
            'pos_disable_price/static/src/js/disable_price.js',
            'pos_disable_price/static/src/css/disable_price.css',
        ],
    },
    'installable': True,
    'application': False,
}