# -*- coding: utf-8 -*-
# Part of BrowseInfo. See LICENSE file for full copyright and licensing details.
{
    'name': 'Print POS Receipt Report Backend',
    'version': '14.0.0.2',
    'category': 'Point of Sale',
    'summary': 'POS order receipt report from backend pos receipt pdf report POS backend receipt print pos receipt from backend receipt from pos print receipt from backend pos report print from backend print pos receipt report print point of sale receipt from backend pos',
    'description' :"""
         This odoo app helps user to print POS order receipt report from backend, User can easily print pos receipt pdf report from pos order backend view. 
    """,
    'author': 'BrowseInfo',
    'website': 'https://www.browseinfo.com',
    "price": 10,
    "currency": 'EUR',
    'depends': ['base','point_of_sale'],
    'data': [
        'security/ir.model.access.csv',
        'report/report_view.xml',
        'data/pos_order_mail_template.xml',
        'views/pos_order_view.xml',
    ],
    'demo': [],
    'test': [],
    'installable': True,
    'auto_install': False,
    'live_test_url':'https://youtu.be/D9fUBEATUJw',
    "images":['static/description/Banner.png'],
}

