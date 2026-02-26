{
    "name": "POS Refund Policy Enforcer",
    "summary": "Enforce strict refund rules: Chief Cashier only, same branch/company, new session, prevent double full refunds.",
    "version": "14.0.1.0.0",
    "author": "Your Company, OCA contributors",
    "license": "AGPL-3",
    "website": "https://example.com",
    "category": "Point of Sale",
    "depends": [
        "point_of_sale",
        "stock",
        "pos_order_return"
    ],
    "data": [
        "security/pos_refund_security.xml",
        "security/ir.model.access.csv",
        "views/pos_refund_views.xml"
    ],
    "installable": True,
    "application": False,
    "auto_install": False
}