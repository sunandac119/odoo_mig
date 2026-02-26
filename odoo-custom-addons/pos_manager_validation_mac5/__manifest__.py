{
    'name': '[Original] POS Manager Validation using User PIN',
    'version': '14.0.1.2',
    'summary': """Validation of Closing POS, Order Deletion, Order Line Deletion,
                  Discount Application, Order Payment, Price Change and Decreasing Quantity""",
    'description': """
POS Manager Validation using User PIN
=====================================

This module allows validation for certain features on POS UI
if the cashier has no access rights or not a manager

Per Point of Sale, you can define manager validation for the following features:
* POS Closing
* Order Deletion
* Order Line Deletion
* Discount Application
* Order Payment
* Price Change
* Decresing Quantity


Compatibility
-------------

This module is compatible and tested with these modules:
* Restaurant module (pos_restaurant)


Keywords: Odoo POS validation, Odoo POS validate, Odoo POS confirmation, Odoo POS confirm,
Odoo POS checking, Odoo POS check, Odoo POS access, Odoo POS user, user access, access right,
delete order, delete order line, POS closing, closing POS, decrease quantity
""",
    'category': 'Sales/Point of Sale',
    'author': 'MAC5',
    'contributors': ['MAC5'],
    'website': 'https://apps.odoo.com/apps/modules/browse?author=MAC5',
    'depends': [
        'point_of_sale',
    ],
    'data': [
        'views/pos_manager_validation_templates.xml',
        'views/res_users_views.xml',
        'views/pos_config_views.xml',
    ],
    'installable': True,
    'application': False,
    'auto_install': False,
    'images': ['static/description/banner.gif'],
    'price': 24.99,
    'currency': 'USD',
    'support': 'mac5_odoo@outlook.com',
    'license': 'OPL-1',
    'live_test_url': 'https://youtu.be/pk07THpL7Ks',
}
