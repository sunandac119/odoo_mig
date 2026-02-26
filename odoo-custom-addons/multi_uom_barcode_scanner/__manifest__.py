{
    "name": "Multi UOM Barcode Scanner",
    "version": "14.0.1.0.2",
    "author": "ChatGPT",
    "category": "Sales",
    "summary": "Scan barcodes from POS multi UOM lines for product search, UOM, and price lookup",
    "depends": ["sale", "purchase", "stock", "mrp", "product"],
    "data": [
        "views/sale_order_view.xml",
        "views/purchase_order_view.xml",
        "views/stock_picking_view.xml",
        "views/mrp_production_view.xml",
        "views/pricelist_barcode.xml",
    ],
    "installable": True,
    "application": False
}