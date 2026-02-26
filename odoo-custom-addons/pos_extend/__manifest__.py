# -*- coding: utf-8 -*-
{
    'name': "POS Extend",
    'summary': "POS Extend",
    'description': "POS Extend",
    'author': "Vansika Gorana",
    'category': 'Point Of Sale',
    'version': '14.0.0.7',
    'depends': ['base','account','point_of_sale'],
    'data': [
        'security/ir.model.access.csv',
        'data/ir_sequence_data.xml',
        'views/pos_assets_common.xml',
        'views/views.xml',
        'views/cash_box_out_report.xml',
		'reports/open_drawer_report.xml',
    ],
    'qweb': [
        'static/src/xml/CashBoxPopup.xml',
        'static/src/xml/CashButton.xml',
    ]
}
