# -*- coding: utf-8 -*-
{
    'name': 'POS Summary Report',
    'summary': """'Print session wise starting and closing and available cash and bank sales'""",
    'description': """Print session wise starting and closing and available cash and bank sales""",
    'version': '14.0',
    'author': "Preciseways",
    'category': "Point of Sale",
    'depends': ['point_of_sale'],
    'data': [
        'security/ir.model.access.csv',
        'security/pos_security.xml',
        'views/pos_report_xls.xml',
		'reports/pos_report_pdf_template.xml',
        'wizard/pos_report_wizard.xml',
    ],
    'installable': True,
    'application': False,
    'price': 10,
    'currency': 'EUR',
    'images':['static/description/banner.png'],
    'license': 'OPL-1',
}
