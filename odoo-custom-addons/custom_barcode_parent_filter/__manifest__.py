{
    "name": "Barcode Scanner Parent Product Filter",
    "version": "14.0.1.0.0",
    "depends": ["stock_barcode"],
    "author": "YourCompany",
    "category": "Warehouse",
    "data": ["views/assets.xml"],
    "assets": {
        "web.assets_backend": [
            "custom_barcode_parent_filter/static/src/js/barcode_filter.js"
        ]
    },
    "installable": True,
    "application": False
}
