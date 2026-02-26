{
    "name": "Inventory HTML5 QR Code Scan",
    "version": "14.0.1.0.0",
    "author": "ChatGPT",
    "depends": ["stock", "stock_barcode"],
    "category": "Inventory",
    "data": [
        "views/inventory_line_scan_view.xml"
    ],
    "assets": {
        "web.assets_backend": [
            "https://unpkg.com/html5-qrcode", 
            "stock_inventory_html5_qrcode_scan/static/src/js/html5_barcode_scanner.js"
        ]
    },
    "installable": True,
    "application": False
}
