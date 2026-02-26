{
    'name': 'Multi UoM Barcode',
    'version': '14.0.1.0.0',
    'summary': 'Different barcodes for different UoMs and price support in price list',
    'category': 'Product',
    'author': 'Your Company',
    'depends': ['base', 'product', 'sale', 'purchase', 'stock', 'point_of_sale'],
    'data': [
        'security/ir.model.access.csv',
        'views/product_template_view.xml',
    ],
    'installable': True,
    'application': False,
}
