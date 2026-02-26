{
    'name': 'POS Session Cash Register Difference Restriction',
    'version': '14.0.1.0',
    'category': 'Point of Sale',
    'summary': 'Makes the cash_register_difference field read-only for non-accounting/advisor users',
    'description': """
        This module restricts editing the cash_register_difference field in the POS session for users 
        who are not part of the Accounting/Advisor group.
    """,
    'author': 'Your Name',
    'depends': ['point_of_sale', 'account'],
    'data': [
        'views/pos_session_view.xml',
    ],
    'installable': True,
    'application': False,
}
