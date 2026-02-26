# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

{
    "name": "Odoo Business Intelligence",
    "version": "14.0.2.0",
    "category": "Analytic",
    "summary": "AI module predicts sales and purchase metrics, enhancing decision-making and optimizing inventory and procurement.",
    "description": """
        Provides sale and purchase forecasting prediction report
    """,
    "author": "Silver Touch Technologies Limited",
    "website": "https://www.silvertouch.com",
    "support": "",
    "depends": ["base", "sale", "purchase", "sale_management"],
    "data": [
        # DATA
        "data/forecasting_cron.xml",

        # SECURITY
        "security/ir.model.access.csv",

        # VIEWS
        "views/sale_forecasting_report_view.xml",
        "views/purchase_forecasting_report.xml",
        "views/menus.xml"
    ],
    "price": 0,
    "currency": "USD",
    "license": "LGPL-3",
    "installable": True,
    'images': ['static/description/banner.png'],
}
