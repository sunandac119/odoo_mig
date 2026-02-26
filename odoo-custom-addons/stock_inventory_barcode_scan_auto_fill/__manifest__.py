{
    "name": "Inventory Barcode Scan & Auto Fill",
    "version": "14.0.1.0.0",
    "author": "ChatGPT",
    "depends": ["stock", "stock_barcode"],
    "category": "Inventory",
    "data": [
        "views/inventory_line_scan_view.xml"
    ],
    "assets": {
        "web.assets_backend": [
            "stock_inventory_barcode_scan_auto_fill/static/src/js/inventory_barcode_scanner.js"
        ]
    },
    "installable": True,
    "application": False
}
