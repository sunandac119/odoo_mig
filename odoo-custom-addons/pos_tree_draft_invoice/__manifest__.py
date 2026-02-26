{
    'name': 'POS Tree Create Invoice',
    'version': '14.0.1.0.0',
    'summary': 'Add Create Invoice action for POS Orders in the tree view',
    'author': 'Your Name or Company',
    'license': 'AGPL-3',
    'depends': ['point_of_sale', 'account'],
    'data': [
        'views/pos_order_view.xml',
    ],
    'installable': True,
    'application': False,
}