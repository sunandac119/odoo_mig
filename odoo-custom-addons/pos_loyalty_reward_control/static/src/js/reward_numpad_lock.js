odoo.define('pos_loyalty_reward_control.reward_numpad_lock', function (require) {
    'use strict';

    const NumpadWidget = require('point_of_sale.NumpadWidget');

    const superClick = NumpadWidget.prototype.onClickButton;

    NumpadWidget.prototype.onClickButton = function (button) {
        const order = this.env.pos.get_order();
        const line = order && order.get_selected_orderline();

        // Block Qty button for reward lines
        if (line && line.reward_id && button === 'quantity') {
            return;
        }
        return superClick.apply(this, arguments);
    };
});
