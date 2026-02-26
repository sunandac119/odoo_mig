# -*- coding: utf-8 -*-

{
    'name': 'Malaysia - Accounting - Trading Company',
    'author': 'Vanshika Gorana',
    'version': '14.0.0',
    'summary': """Chart of Account Malaysia""",
    'category': 'Localization',
    'license': 'LGPL-3',
    'description': """
Malaysia Chart of Accounts for Trading Company.
=======================================================

This module Install The Chart of Accounts of Malaysia, including SST and GST code, for Trading Company.


    """,
    'depends': ['base', 'account', 'l10n_generic_coa'],
    'data': [
        'data/account_coa_data.xml',
        'data/account_coa_base.xml',
        'views/res_company_view.xml',
        'views/account_view.xml',
    ],
    'installable': True,
    'application': True,
    'auto_install': False,
   
}
