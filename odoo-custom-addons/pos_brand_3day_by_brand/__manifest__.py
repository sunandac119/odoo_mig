# -*- coding: utf-8 -*-
{
    "name": "POS 3-Day Sales by Brand (Pages)",
    "version": "14.0.1.0",
    "summary": "PDF: 3-day POS sales - products grouped by brand, new page per brand; filters by Sales Team & Warehouse",
    "category": "Inventory/Reporting",
    "author": "ChatGPT",
    "depends": ["point_of_sale", "stock", "sales_team"],
    "data": [
        "security/ir.model.access.csv",
        "views/brand_3day_by_brand_wizard_views.xml",
        "data/report_action.xml",
        "reports/brand_3day_by_brand_templates.xml"
    ],
    "installable": True,
    "application": False,
}
