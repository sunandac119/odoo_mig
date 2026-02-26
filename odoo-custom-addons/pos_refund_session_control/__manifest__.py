{
    "name": "POS Refund Session Control",
    "version": "14.0.1.0.0",
    "summary": "Allow refund with session auto-creation and config-based control",
    "category": "Point of Sale",
    "author": "ChatGPT",
    "license": "AGPL-3",
    "depends": ["point_of_sale"],
    "data": [
        "security/ir.model.access.csv",
        "views/pos_config_view.xml",
    ],
    "installable": True,
    "application": False,
}
