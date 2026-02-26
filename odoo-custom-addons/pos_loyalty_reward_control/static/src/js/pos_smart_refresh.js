
odoo.define('pos_loyalty_reward_control.smart_refresh', function (require) {
    'use strict';

    const models = require('point_of_sale.models');

    const OrderSuper = models.Order.prototype;

    models.Order = models.Order.extend({

        async set_client(partner) {
            await OrderSuper.set_client.apply(this, arguments);
            if (!partner || !this.pos?.env?.services?.rpc) return;

            try {
                const res = await this.pos.env.services.rpc({
                    model: 'res.partner',
                    method: 'read',
                    args: [[partner.id], ['name', 'phone', 'email', 'loyalty_points']],
                });
                if (res && res.length) {
                    this.pos.db.add_partners(res);
                    OrderSuper.set_client.call(this, res[0]);
                    this.pos.last_refresh_time = new Date();
                }
            } catch (e) {
                console.warn('Smart refresh (customer select) failed', e);
            }
        },

        async finalizeValidation() {
            await OrderSuper.finalizeValidation.apply(this, arguments);
            if (!this.pos?.env?.services?.rpc) return;

            try {
                const partner = this.get_client();
                if (partner) {
                    const res = await this.pos.env.services.rpc({
                        model: 'res.partner',
                        method: 'read',
                        args: [[partner.id], ['loyalty_points']],
                    });
                    if (res && res.length) {
                        this.pos.db.add_partners(res);
                        this.pos.last_refresh_time = new Date();
                    }
                }
            } catch (e) {
                console.warn('Smart refresh (after payment) failed', e);
            }
        },

    });
});
