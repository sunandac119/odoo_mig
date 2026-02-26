
{
    "name": "Low Sales Report Analysis V8.1",
    "version": "1.0.01",
    "category": "Sales",
    "summary": "Low Sales Reporting with Pivot and Carton Qty Conversion",
    "author": "Generated",
    "depends": ["sale", "stock"],
    "data": [
        "security/ir.model.access.csv",
        "views/low_sales_report_view.xml",
        "views/low_sales_report_pivot_view.xml",
        "data/cron_refresh_mv.xml"
    ],
    "installable": True,
    "application": True,
    "auto_install": False,
}
