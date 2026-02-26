# -*- coding: utf-8 -*-
{
    'name': 'BI Materialized View Report',
    'version': '1.0',
    'category': 'Reporting',
    'summary': 'Sales and Performance Summary Reports via Materialized Views',
    'author': 'ChatGPT',
    'depends': ['base', 'sale', 'purchase', 'account'],
    'data': [
        'security/ir.model.access.csv',
        'views/bi_report_views.xml',
    ],
    'installable': True,
    'auto_install': False,
}
