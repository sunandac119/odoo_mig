# -*- coding: utf-8 -*-
##############################################################################
#
#    TL Technology
#    Copyright (C) 2019 ­TODAY TL Technology (<https://www.posodoo.com>).
#    Odoo Proprietary License v1.0 along with this program.
#
##############################################################################
{
    'name': "POS Ui Design",
    'version': '1.0.0.2',
    'category': 'Point of Sale',
    'author': 'TL Technology',
    'live_test_url': 'http://posodoo.com',
    'price': '0',
    'website': 'http://posodoo.com',
    'sequence': 0,
    'depends': [
        'point_of_sale',

    ],
    'demo': [],
    'data': [
        'security/ir.model.access.csv',
        'template/ImportLibrary.xml',
        'views/PosConfig.xml',
        'views/PosUi.xml'
    ],
    'qweb': [
        'static/src/xml/*.xml'
    ],
    "currency": 'EUR',
    "external_dependencies": {
        "python": [],
        "bin": []
    },
    'images': ['static/description/icon.png'],
    'support': 'thanhchatvn@gmail.com',
    "license": "OPL-1",
    'installable': True,
    'application': True,
}
