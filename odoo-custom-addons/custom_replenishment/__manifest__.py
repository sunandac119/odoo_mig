# -*- coding: utf-8 -*-
##############################################################################
# Author      : Acespritech Solutions Pvt. Ltd. (<www.acespritech.com>)
# Copyright(c): 2012-Present Acespritech Solutions Pvt. Ltd.
# All Rights Reserved.
#
# This program is copyright property of the author mentioned above.
# You can`t redistribute it and/or modify it.
#
##############################################################################
{
    'name': 'Custom Replenishment',
    'version': '14.0.1.0.1',
    'category': 'Replenishment',
    'description': """

    """,
    'summary': 'custom feidls for replenishment of Product',
    'author': 'Acespritech Solutions Pvt. Ltd.',
    'price': '',
    'currency': '',
    'depends': ['base', 'product', 'stock','custom_product'],
    'data': [
            'views/replenishment_inherited_list_view.xml'
    ],
    'installable': True,
    'application': True,
    'auto_install': False,
}

# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:
