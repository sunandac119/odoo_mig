# -*- coding: utf-8 -*-
{
    'name': 'Product Multi Barcode for POS and Sales, Purchase',
    'author': 'Edge Technologies',
    'version': '14.0.1.2',
    "live_test_url":'https://youtu.be/BCUzYYfsFis',
    "images":['static/description/main_screenshot.png'],
    'summary': 'Multiple barcode for product multi barcode for sales multiple barcode of product pos multi barcode pos multiple barcode purchase multiple barcode pos multiple barcode point of sale multiple barcode multi barcode for product pos multiple barcode for pos.',
    'description': """
        App helps to add multiple barcode for a product and product variant in sales, purchase & point of sale. you can search the product or the product variant with any of the barcode number. also product multi barcode for sales multiple barcode features of product for sales order, purchase order & point of sale. odoo provides unique barcode for product and product variants but some times it requires to manage multiple barcode for one product or different/multiple barcode for each variant. sales and point of sale barcode module helps you setup multiple barcode for single product or product variant and use in sales, purchase and point of sale in odoo. with this app, you can also search the product or product variant with any of the barcode. product multiple barcode sales multiple barcode purchase multiple barcode pos multiple barcode point of sale multiple barcode multiple barcode for product variants multiple barcode for sales order multiple barcode for pos multiple barcode for point of sale product multi barcode sales multi barcode pos multi barcode point of sale multi barcode multi barcode for product variants multi barcode for sales order multi barcode for pos multi barcode for point of sale.
    """,
    "license" : "OPL-1", 
    'depends': ['base','sale_management','point_of_sale','purchase'],
    'data': [
            'security/ir.model.access.csv',
            'views/product_template_view.xml',],
    'installable': True,
    'auto_install': False,
    'application': True,
    'price':15,
    'currency': "EUR",
    'category': 'Point of Sale',
    
}
