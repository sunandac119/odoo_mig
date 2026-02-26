{
    'name': 'Auto POS Rounding (Auto UP and DOWN Rounding)',
    'version': '14.3.2.1',
    'sequence': 1,
    'summary': 'POS Auto Rounding Amount based on the Digits and Points(Communnity & Enterprise)',
    'price': 15,
    'currency': 'EUR',
    "author" : "MAISOLUTIONSLLC",
    "email": 'apps@maisolutionsllc.com',
    "website":'http://maisolutionsllc.com/',
    'description': "Using this module you can set auto up and down rounding for Digits based and Point based. here there is s button for and that will perform auto rounding.  and here using this module AUTO UP and DOWN rounding will be apply on POS order total amount.",
    'license': 'OPL-1', 
    'category': 'Point Of Sale',
    'depends': ['base', 'point_of_sale'],
    'data': [
        'views/assets.xml',
        'views/point_of_sale.xml',
        'views/pos_config_view.xml',
    ],
    'images': ['static/description/main_screenshot.png'],
    "live_test_url" : "https://youtu.be/z1VqOGi_oNY ", 
    'qweb': [
        'static/src/xml/payment.xml',
        'static/src/xml/receipt.xml'
    ],
    'installable': True,
    'application': True,
}
