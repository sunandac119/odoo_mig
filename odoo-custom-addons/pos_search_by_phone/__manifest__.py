{
    'name': 'POS Customer Search by Phone',
    'version': '14.0.1.0.0',
    'category': 'Point of Sale',
    'depends': ['point_of_sale'],
    'data': [],
    'assets': {
        'point_of_sale.assets': [
            'pos_custom/static/src/js/pos_customer_search.js',
        ],
    },
    'installable': True,
    'application': False,
}
