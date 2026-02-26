# -*- coding: utf-8 -*-
##############################################################################
#
# Copyright 2019 EquickERP
#
##############################################################################

{
    'name': "Inventory Valuation Report",
    'category': 'Stock',
    'version': '14.0.1.5',
    'author': 'Equick ERP',
    'description': """
        This Module allows you to generate Inventory Valuation Report PDF/XLS wise.
    """,
    'summary': """Inventory Report | Valuation Report | Real Time Valuation Report | Real Time Stock Report | Stock Report | Stock card | Stock Valuation Report | Odoo Inventory Report | stock card report | stock card valuation report | stock balance""",
    'depends': ['base', 'stock_account', 'website_sale', 'point_of_sale'],
    'price': 60,
    'currency': 'EUR',
    'license': 'OPL-1',
    'website': "",
    'data': [
        'security/ir.model.access.csv',
        'wizard/wizard_inventory_valuation_view.xml',
        'report/report.xml',
        'report/inventory_valuation_report.xml',
        'report/inventory_valuation_report_format.xml',
    ],
    'images': [],
    'installable': True,
    'auto_install': False,
    'application': False,
}

# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:
