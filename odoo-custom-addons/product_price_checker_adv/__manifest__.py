# -*- coding: utf-8 -*-
#################################################################################
# Author      : CFIS (<https://www.cfis.store/>)
# Copyright(c): 2017-Present CFIS.
# All Rights Reserved.
#
#
#
# This program is copyright property of the author mentioned above.
# You can`t redistribute it and/or modify it.
#
#
# You should have received a copy of the License along with this program.
# If not, see <https://www.cfis.store/>
#################################################################################

{
    "name": "Price Checker | Product Price Checker | Product Checker | Product Price Checker kiosk (Prices per minimum quantity)",
    "summary": """
        This module to allows customers to check product details using barcode. 
        Also, it will be useful to display prices per minimum quantity based on the pricelist set up for the price checker.
    """,
    "version": "14.0.2",
    "description": """
        This module to allows customers to check product details using barcode. 
        Also, it will be useful to display prices per minimum quantity based on the pricelist set up for the price checker.
        Price Checker
        Product Price Checker
        Product Checker
        Product Price Checker kiosk
        Prices per minimum quantity
    """,    
    "author": "CFIS",
    "maintainer": "CFIS",
    "license" :  "Other proprietary",
    "website": "https://www.cfis.store",
    "images": ["images/product_price_checker_adv.png"],
    "category": "Sales",
    "depends": [
        "product",
        "sale_management",
    ],
    "data": [
        "security/security.xml",
        "views/assets.xml",
        "views/product_price_checker_view.xml",
        "views/res_config_settings_views.xml",
    ],
    "qweb": [
        'static/src/xml/price_checker.xml',
    ], 
    "installable": True,
    "application": True,
    "price"                 :  38.00,
    "currency"              :  "EUR",
    "pre_init_hook"         :  "pre_init_check",
}