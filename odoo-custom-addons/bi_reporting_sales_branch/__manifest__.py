{
    'name': 'BI Reporting - Sales Branch',
    'version': '14.0.1.0.0',
    'summary': 'Daily Sales by Branch Reporting under BI Menu',
    'category': 'Reporting',
    'author': 'Generated',
    'depends': ['base', 'point_of_sale', 'sale_management'],
    'data': [
        'security/ir.model.access.csv',
        'views/bi_daily_sales_by_branch_mv_views.xml',
        'data/ir_cron.xml'
    ],
    'installable': True,
    'auto_install': False,
}