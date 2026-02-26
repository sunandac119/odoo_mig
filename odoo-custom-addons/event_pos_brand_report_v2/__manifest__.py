# -*- coding: utf-8 -*-
{
    'name': 'Event POS Brand PDF Report (Sales Team + CTN)',
    'version': '14.0.2.0.1',
    'summary': 'Yesterday POS brands by Sales Team; list all products per brand; optional CTN Qty column; pages per brand',
    'category': 'Point of Sale',
    'author': 'YourCompany',
    'license': 'LGPL-3',
    'depends': ['point_of_sale', 'crm'],
    'data': [
        'security/ir.model.access.csv',
        'report/event_pos_brand_templates.xml',
        'report/event_pos_brand_report.xml',
        'views/event_pos_brand_wizard_views.xml',
    ],
    'installable': True,
}
