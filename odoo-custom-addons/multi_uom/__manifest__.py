
{
    "name": "Multi UoM",
    "version": "14.0.1.0.0",
    "summary": "Supports multiple units of measure per product with barcodes and pricing",
    "category": "Product",
    "author": "ChatGPT",
    "depends": ["product"],
    "data": [
        "views/product_template_views.xml",
    ],
    "installable": True,
    "application": False,
    "assets": {
        "point_of_sale.assets": [
            "multi_uom/static/src/js/pos_multi_uom.js",
        ],
    },
}
