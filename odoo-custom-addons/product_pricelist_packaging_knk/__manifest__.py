# -*- coding: utf-8 -*-
#################################################################################
# Author      : Kanak Infosystems LLP. (<https://www.kanakinfosystems.com/>)
# Copyright(c): 2012-Present Kanak Infosystems LLP.
# All Rights Reserved.
#
#
# This program is copyright property of the author mentioned above.
# You can`t redistribute it and/or modify it.
#
#
# You should have received a copy of the License along with this program.
# If not, see <https://www.kanakinfosystems.com/license>
#################################################################################

{
    "name": "Product Pricelist Packaging",
    "version": "14.0.1.1",
    "summary": "By using this module user can set product packaging price and quantity",
    'description': """By using this module user can set product packaging price and quantity| product
        packaging | price | packaging price |product packaging| packaging product| set price |product categories.
    """,
    'license': 'OPL-1',
    "category": "Sales/Sales",
    "website": "https://www.kanakinfosystems.com",
    'author': 'Kanak Infosystems LLP.',
    'images': ['static/description/banner.gif'],
    "depends": ['sale_stock', 'purchase_stock'],
    "data": [
        'views/sale_order_views.xml',
        'views/product_template_views.xml',
        'views/pricelist_views.xml',
        'views/account_move_views.xml',
    ],
    'sequence': 1,
    "application": True,
    "installable": True,
    "currency": 'EUR',
    "price": '25',
}
