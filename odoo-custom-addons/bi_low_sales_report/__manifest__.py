# -*- coding: utf-8 -*-
# Part of BrowseInfo. See LICENSE file for full copyright and licensing details.
{
    "name" : "Sales Low Product Report | Lower Sales Report",
    "version" : "14.0.0.0",
    "category" : "Sales",
    'summary': 'Product Low Sales Report for Under Performing Products Sale Report for Poor Products Sales Report for Low Performance Sale Report Set Date Range for Lower Product Sales Report Poor Sales Report Low Sales PDF Report for Low Performance Products Sale Report',
    "description": """ 

        Sales Low Product Report Odoo App helps users to take out reports of poorly performing products. User can configure default criteria for product quantity and amount to print low sales report. User have option to select report type like product, product variants and product category between any of the date range to print low sales report. User can print low sales report in PDF and XLS format and also display low sales report analysis in pivot view.

    """,
    "author": "BrowseInfo",
    "website" : "https://www.browseinfo.com",
    "depends" : ['base','sale_management','stock'],
    "data": [
            'security/ir.model.access.csv',
            'wizard/low_sales_report_view.xml',
            'report/low_sales_report.xml',
            'report/low_sales_report_template.xml',
            'views/res_config_setting_views.xml',
            'views/excel_report.xml',
            'views/low_sales_pivot_views.xml',
            ],
    'license':'OPL-1',
    'installable': True,
    'auto_install': False,
    'live_test_url':'https://youtu.be/5eDC5iOWPLs',
    "images":['static/description/Sales-Low-Product-Report-Banner.gif'],
}
