/** @odoo-module **/

odoo.define('pos_disable_price.NumpadWidgetDisablePrice', function (require) {
    'use strict';

    const Registries = require('point_of_sale.Registries');
    const NumpadWidget = require('point_of_sale.NumpadWidget');

    // Minimal patch: block entering 'price' mode for everyone.
    const DisablePrice = (Numpad) => class extends Numpad {
        get hasPriceControlRights() {
            return false; // Always deny price control
        }
        mounted() {
            if (super.mounted) {
                super.mounted();
            }
            // If somehow active mode is 'price', force it back to 'quantity'
            if (this.props.activeMode === 'price') {
                this.trigger('set-numpad-mode', { mode: 'quantity' });
            }
        }
        changeMode(mode) {
            if (mode === 'price') {
                // Block switching to price mode completely
                return;
            }
            super.changeMode(mode);
        }
    };

    Registries.Component.extend(NumpadWidget, DisablePrice);
});