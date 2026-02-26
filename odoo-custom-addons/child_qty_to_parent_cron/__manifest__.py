{
    "name": "Child Qty to Parent Cron",
    "version": "14.0",
    "depends": ["sale", "stock"],
    "author": "",
    "category": "Inventory",
    "description": "Transfers child qty to parent and sets child qty to 0 via cron.",
    "data": ["data/ir_cron.xml",
             "views/server_action.xml"],
    "installable": True,
    "auto_install": False,
    "application": False,
    "license": "LGPL-3"
}
