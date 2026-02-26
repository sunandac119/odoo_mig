# -*- coding: utf-8 -*-
# This module and its content is copyright of Technaureus Info Solutions Pvt. Ltd.
# - © Technaureus Info Solutions Pvt. Ltd 2020. All rights reserved.

{
    'name': 'POS Margin And Analysis',
    'version': '14.0.0.8',
    'category': 'Point of Sale',
    'summary': 'POS Margin and Analysis',
    'sequence': 1,
    'author': 'Technaureus Info Solutions Pvt. Ltd.',
    'website': 'http://www.technaureus.com/',
    'description': """
    """,
    'price': 8,
    'currency': 'EUR',
    'license': 'Other proprietary',
    'depends': ['point_of_sale'],
    'data': [
        'views/point_of_sale.xml',
        'views/pos_order_view.xml'
    ],
    'images': ['images/margin_screenshot.png'],
    'installable': True,
    'application': True,
    'auto_install': False,
    'post_init_hook': 'load_cost_post_init_hook',
    'qweb': [],
    'live_test_url': 'https://www.youtube.com/watch?v=xkObQBFA0hc&t=54s'

}
