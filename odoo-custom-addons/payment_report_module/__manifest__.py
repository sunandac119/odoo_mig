{
    'name': 'Payment Report Module',
    'version': '1.0',
    'category': 'Accounting',
    'description': 'Custom report for daily payment checklist',
    'depends': ['base', 'account'],
    'data': [
        'views/report_payment_action.xml',        
    ],
    'installable': True,
    'application': False,
}
