odoo.define('mai_pos_roundoff_updown_auto.PaymentScreen', function (require) {
    'use strict';

    const PaymentScreen = require('point_of_sale.PaymentScreen');
    const Registries = require('point_of_sale.Registries');

    const CstmPaymentScreen = PaymentScreen =>
        class extends PaymentScreen {
            constructor() {
                super(...arguments);
                this.env.pos.get_order().set_rounding_status(true);
                this.render();
            }
        };

    Registries.Component.extend(PaymentScreen, CstmPaymentScreen);
    return PaymentScreen;
});
