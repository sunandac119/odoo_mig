{
    'name': 'Restrict Sale Discount Editing',
    'version': '14.0.1.0.0',
    'summary': 'Only certain users can edit sale discount field',
    'depends': ['sale'],
    'data': [
        'security/sale_discount_groups.xml',
        'views/sale_order_discount_view.xml',
    ],
    'installable': True,
    'application': False,
}
