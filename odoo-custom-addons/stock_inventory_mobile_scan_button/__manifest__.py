{
    "name": "Stock Inventory Mobile Scan Button",
    "version": "14.0.1.0.0",
    "author": "ChatGPT",
    "depends": ["stock", "stock_barcode"],
    "category": "Inventory",
    "data": [
        "views/inventory_line_scan_button_view.xml"
    ],
    "assets": {
        "web.assets_backend": [
            "stock_inventory_mobile_scan_button/static/src/js/inventory_barcode_scanner.js"
        ]
    },
    "installable": True,
    "application": False,
}
