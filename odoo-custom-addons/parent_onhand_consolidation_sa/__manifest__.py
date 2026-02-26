# -*- coding: utf-8 -*-
{
    'name': 'Parent On-hand Consolidation Server Action',
    'version': '14.0.1.0.0',
    'category': 'Inventory',
    'summary': 'Consolidate child product stock to parent using server action',
    'depends': ['stock'],
    'data': [
        'data/server_action_and_cron.xml',
    ],
    'installable': True,
    'application': False,
    'auto_install': False,
}
