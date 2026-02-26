from .data.menu_patch import patch_top_level_menus

def post_init_hook(cr, registry):
    patch_top_level_menus(cr, registry)