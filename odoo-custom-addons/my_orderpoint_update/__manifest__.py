{
    'name': 'Orderpoint Quantity Update',
    'version': '1.0.6',
    'category': 'Stock',
    'summary': 'Custom module to update warehouse orderpoint quantities based on on-hand quantities.',
    'description': """
        This module calculates the sum of on-hand quantity multiplied by unit quantity 
        for the same parent product template and warehouse, and updates the stock.warehouse.orderpoint.
    """,
    'author': 'Your Name',
    'depends': ['stock'],
    'data': [],
    'installable': True,
    'application': False,
}
