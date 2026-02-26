{
    "name": "BI Stock & Sales Summary Report",
    "version": "14.0.1.0.0",
    "summary": "Sales Summary and Stock Ordering Reports with Materialized Views",
    "category": "Inventory",
    "depends": ["stock", "sale", "point_of_sale"],
    "data": [
        "views/sale_summary_report_views.xml",
        "views/bi_report_menus.xml"
    ],
    "installable": True,
    "application": False
}
