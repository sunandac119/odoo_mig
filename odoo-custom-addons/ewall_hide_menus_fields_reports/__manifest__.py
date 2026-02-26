# -*- coding: utf-8 -*-
{
    'name': "Hide Menus, Hide Fields and Hide Reports",

    'summary': 'Hide Menus, Hide Fields and Hide Reports',

    'description': """
        Hide Any Menu, Sub-Menu And Report From User Configuration On User Form View
        Hide Any Menu, Sub-Menu And Report From User Configuration On Menu Form View
        Hide Report From Menu, User Configuration On Report Form View
        Hide, Set Readonly Any Field From Any Group And Its Users Configuration On Models Form View.
    """,

    'author': "EWall Solutions Pvt. Ltd.",
    'website': "https://www.ewallsolutions.com",
    'company': "Ewall Solutions Pvt. Ltd.",
    'support':'support@ewallsolutions.com',
    'currency':'USD',
    'price':'10.00',
    'category': 'Extra Tools',
    'version': '14.0',
    'license': 'OPL-1',
    'depends': ['base'],
    'data': [
        'security/ir.model.access.csv',
        'views/ir_action_reports.xml',
        'views/ir_model.xml',
        'views/res_groups.xml',
        'views/res_users.xml',
    ], 
    
    'installable': True,

     'images': [
        'static/description/images/banner.jpg',
    ],
}
