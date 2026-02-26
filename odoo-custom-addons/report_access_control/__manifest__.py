{
    'name': 'Report Access Control',
    'version': '14.0.1.0.1',
    'summary': 'Restrict all reporting to Report Users group only',
    'author': 'ChatGPT',
    'depends': ['base', 'sale', 'account', 'stock', 'point_of_sale'],
    'data': [
        'security/report_group.xml',
        'security/report_access_rights.xml',
    ],
    'installable': True,
    'auto_install': False,
}
