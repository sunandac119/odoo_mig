{
    'name': 'Update Standard Price',
    'version': '14.0.1.0.1',
    'summary': 'Cron job to update standard price based on last purchase cost',
    'description': 'This module updates the standard price of products based on the last purchase cost every day.',
    'author': 'Your Name',
    'depends': ['base', 'product', 'purchase', 'stock'],
    'data': [
        'data/ir_cron_data.xml',
    ],
    'installable': True,
    'application': False,
}
