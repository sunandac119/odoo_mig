
{
    'name': 'Replenishment Report',
    'version': '1.1',
    'category': 'Inventory',
    'summary': 'Custom replenishment report by parent template',
    'description': 'A module to generate replenishment reports for products grouped by parent templates.',
    'depends': ['stock'],
    'data': [
        'views/replenishment_report_views.xml',
        'views/replenishment_by_parent_views.xml',
    ],
    'installable': True,
    'application': False,
}
