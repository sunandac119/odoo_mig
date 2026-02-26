odoo.define('pos_loyalty_reward_control.reward_qty_lock', function (require) {
    'use strict';

    const models = require('point_of_sale.models');

    const superSetQty = models.Orderline.prototype.set_quantity;

    models.Orderline.prototype.set_quantity = function (qty, keep_price) {
        // Lock quantity changes for reward lines
        if (this.reward_id) {
            return;
        }
        return superSetQty.apply(this, arguments);
    };
});
