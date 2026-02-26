# -*- coding: utf-8 -*-
{
    "name": "Product Label: Multi-UoM Barcodes",
    "version": "14.0.2.0.1",
    "summary": "Print labels selecting multiple barcodes per UoM (with Print-menu bindings)",
    "author": "ChatGPT",
    "license": "LGPL-3",
    "depends": ["base", "product", "uom", "web", "garazd_product_label", "stock"],
    "data": [
        "security/ir.model.access.csv",
        "views/label_barcode_wizard_views.xml",
        "views/product_views.xml",
        "views/print_bindings.xml",
        "reports/product_report_hide.xml",
        "reports/product_label_templates.xml",
        "reports/report_label_templates.xml",
        "reports/product_product_templates.xml",
        "reports/prodduct_product_report.xml",
        "reports/stick_report_picking_copy_2.xml",
    ],
    "application": False,
}
