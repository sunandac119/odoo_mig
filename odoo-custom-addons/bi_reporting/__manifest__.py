{
    'name': 'BI Reporting',
    'version': '14.0.1.0',
    'summary': 'Materialized BI Reports for Sales, Inventory, Expenses',
    'category': 'Reporting',
    'author': 'Your Company',
    'depends': ['base', 'sale', 'point_of_sale', 'crm', 'stock', 'account'],
    'data': [
        'views/bi_sales_summary_mv_views.xml',
        'views/bi_inventory_summary_mv_views.xml',
        'views/bi_expense_summary_mv_views.xml',
        'views/bi_reporting_menu.xml',
        'wizards/wizard_bi_sales_filter.xml',
        'data/cron.xml',
    ],
    'installable': True,
    'application': True,
}
