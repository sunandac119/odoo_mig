# -*- coding: utf-8 -*-
{
    'name': 'Candy Pool Repacking Wizard',
    'version': '14.0.1.0.0',
    'summary': 'Barcode-based repacking from FMCG packs (unit) into Candy Pool bulk (kg) with cost/kg',
    'category': 'Inventory',
    'author': 'Custom',
    'license': 'LGPL-3',
    'depends': ['stock', 'product'],
    'data': [
        'security/candy_repack_groups.xml',
        'security/ir.model.access.csv',
        'data/candy_repack_location.xml',
        'views/candy_repack_menu.xml',
        'views/candy_repack_wizard_views.xml',
    ],
    'installable': True,
    'application': False,
}
