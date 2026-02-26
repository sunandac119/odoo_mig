# -*- coding: utf-8 -*-
{
    "name" : "POS Access Rights",
    "version" : "1.0",
    "category" : "Point of Sale",
    'summary': 'This apps helps you to Allow/Disable POS Features like Discount, Change Price, Payment, Quantity, Remove Orderline | Allow/Disable pos features | Restriction of POS User | POS Access Rules | Point of Sale Access Rights',
    'author': "Preway IT Solutions",
    "depends" : ['point_of_sale', 'hr'],
    "data": [
        'views/assets.xml',
        'views/res_users_view.xml',
    ],
    'qweb': [
        'static/src/xml/pw_disable_pos_features.xml',
    ],
    "price": 15,
    "currency": 'EUR',
    "auto_install": False,
    "installable": True,
    "live_test_url": 'https://youtu.be/UvAB8Qwt0e4',
    "images":['static/description/Banner.png'],
}
