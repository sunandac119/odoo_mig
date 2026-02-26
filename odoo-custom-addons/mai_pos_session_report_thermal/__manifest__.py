{
    'name': 'POS Session Report | POS Z Report | POS Session Z Report | Session Cash In Out',
    'description': """
     Using this module you can print POS Session Report or Z Report from frontend end Using Thermal Printer.
    """,    
    'version': '14.1.1.1',
    'sequence': 1,
    'email': 'apps@maisolutionsllc.com',
    'website':'http://maisolutionsllc.com/',
    'category': 'Point of Sale',
    'summary': 'Using this module you can print POS Session Report or Z Report from frontend end Using Thermal Printer.',
    'author': 'MAISOLUTIONSLLC',
    'price': 11,
    'currency': 'EUR',
    'license': 'OPL-1',    
    'depends': ['point_of_sale'],
    'qweb': [
             'static/src/xml/mai_session_report.xml',
             ],
    "data": [
        'views/templates.xml',
        'views/pos_config_view.xml',
        'report/report_pos_session.xml',
    ],
    'images': ['static/description/main_screenshot.png'],
    'demo': [],
    'installable': True,
    'auto_install': False,
    'application': True,
}
