odoo.define('pos_restrict_disc_amt.NumpadWidget', function (require) {
    "use strict";

    const NumpadWidget = require('point_of_sale.NumpadWidget');
    const Registries = require('point_of_sale.Registries');
    const { useState } = owl;

    const RestrictedNumpadWidget = (NumpadWidget) =>
        class extends NumpadWidget {
            setup() {
                super.setup();
                const user = this.env.pos.get_cashier();
                this.state = useState({
                    hasDiscPermission: user?.allow_pos_discount,
                    hasPricePermission: user?.allow_pos_price,
                });
            }

            get isDiscDisabled() {
                return !this.state.hasDiscPermission;
            }

            get isPriceDisabled() {
                return !this.state.hasPricePermission;
            }

            changeMode(mode) {
                if ((mode === 'discount' && this.isDiscDisabled) || 
                    (mode === 'price' && this.isPriceDisabled)) {
                    return; // read-only, do nothing
                }
                super.changeMode(mode);
            }
        };

    Registries.Component.extend(NumpadWidget, RestrictedNumpadWidget);

    return RestrictedNumpadWidget;
});
