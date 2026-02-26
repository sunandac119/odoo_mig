{
    'name': 'POS Loyalty Reward Control (Overlay)',
    'version': '14.0.1.0.0',
    'category': 'Point of Sale',
    'summary': 'Merge same reward into single line and lock reward quantity in POS Loyalty',
    'author': 'Overlay Patch',
    'depends': ['point_of_sale', 'pos_loyalty'],
    'assets': {
        'point_of_sale.assets': [
        'pos_loyalty_reward_control/static/src/js/pos_smart_refresh.js',
        'pos_loyalty_reward_control/static/src/xml/last_refresh_indicator.xml',
        'pos_loyalty_reward_control/static/src/js/refresh_pos_button.js',
        'pos_loyalty_reward_control/static/src/xml/refresh_pos_button.xml',
            'pos_loyalty_reward_control/static/src/js/00_debug_loaded.js',
            'pos_loyalty_reward_control/static/src/js/reward_merge.js',
            'pos_loyalty_reward_control/static/src/js/reward_qty_lock.js',
            'pos_loyalty_reward_control/static/src/js/reward_numpad_lock.js',
        ],
    },
    'installable': True,
    'application': False,
}
