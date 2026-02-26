{
    'name': 'Purchase Price Updater',
    'version': '1.1',
    'category': 'Inventory',
    'summary': 'Update standard_price based on last purchase cost via scheduled cron job',
    'author': 'Your Name',
    'website': 'http://yourwebsite.com',
    'depends': ['base', 'stock', 'purchase'],
    'data': [
        'data/cron.xml',
    ],
    'installable': True,
    'application': False,
    'auto_install': False,
}