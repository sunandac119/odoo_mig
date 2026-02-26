from odoo import api, SUPERUSER_ID
import logging

_logger = logging.getLogger(__name__)

def patch_top_level_menus(cr, registry):
    env = api.Environment(cr, SUPERUSER_ID, {})
    default_icon = 'web/static/src/img/icons/default_icon.svg'

    top_menus = env['ir.ui.menu'].search([
        ('parent_id', '=', False),
        '|', ('web_icon', '=', False), ('web_icon', '=', '')
    ])

    for menu in top_menus:
        menu.web_icon = default_icon
        _logger.info(f"Patched menu: {menu.name} (ID {menu.id}) with default icon")

    _logger.info(f"{len(top_menus)} top-level menus patched successfully.")