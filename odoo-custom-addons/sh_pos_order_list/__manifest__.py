# Copyright (C) Softhealer Technologies.
# Part of Softhealer Technologies.
{
    "name": "Point Of Sale Order List",
    "author": "Softhealer Technologies",
    "website": "https://www.softhealer.com",
    "support": "support@softhealer.com",
    "category": "point of sale",
    "license": "OPL-1",
    "summary": "Point Of Sale Order List,POS Order List,POS all Order List, POS All Order List,Orders List on POS screen,POS Frontend Orders Management, POS Order management, POS Order List Management,manage point of sale orders,pos all order list odoo",
    "description": """Currently, in odoo there is well designed and precisely managed POS system available. But one thing that everyone wanted in pos is the current session order list on POS Main Screen. The main reason behind this feature is you can easy to see previous orders, easy to do re-order, re-print orders without closing the current session.""",
    "version": "14.0.11",
    "depends": ["point_of_sale"],
    "application": True,
    "data": [
        'views/sh_pos_order_list.xml',
        'views/pos_config.xml',
    ],
    "images": ["static/description/background.png", ],
    "qweb": ["static/src/xml/*.xml"],
    "auto_install": False,
    "price": 25,
    "installable": True,
}
