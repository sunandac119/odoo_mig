odoo.define('pos_loyalty_reward_control.reward_merge', function (require) {
    'use strict';

    const models = require('point_of_sale.models');

    // Rewards in Odoo 14 are added via Order.add_reward()
    const superAddReward = models.Order.prototype.add_reward;

    models.Order.prototype.add_reward = function (reward, coupon_id, options) {
        // Merge same reward into single line (identified by reward_id)
        const existing = this.get_orderlines().find(l => l.reward_id === reward.id);
        if (existing) {
            // Increment quantity instead of adding new line
            existing.set_quantity(existing.quantity + 1);
            return existing;
        }
        return superAddReward.apply(this, arguments);
    };
});
