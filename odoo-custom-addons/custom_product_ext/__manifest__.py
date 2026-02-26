{
    'name': 'Custom Product Template',
    'version': '14.0.1.0.1',
    'category': 'Sales',
    'depends': ['base', 'product', 'stock'],
    'data': [
        'views/product_template.xml',
        'views/stock_move_line_view.xml',
        'views/replenishment_inherited_list_view.xml'
    ],
    'installable': True,
}
