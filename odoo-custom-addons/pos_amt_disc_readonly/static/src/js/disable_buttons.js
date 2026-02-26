odoo.define('pos_amt_disc_readonly.disable_buttons', function(require){
    'use strict';

    const NumpadWidget = require('point_of_sale.NumpadWidget');
    const Registries = require('point_of_sale.Registries');

    const ReadOnlyNumpadWidget = (NumpadWidget) =>
        class extends NumpadWidget {
            mounted() {
                super.mounted();

                // Disable Discount button
                const discButton = this.el.querySelector('[data-id="Discount"]');
                if (discButton) {
                    discButton.setAttribute('disabled', 'true');
                }

                // Disable Price (Amount) button
                const priceButton = this.el.querySelector('[data-id="Price"]');
                if (priceButton) {
                    priceButton.setAttribute('disabled', 'true');
                }
            }

            async setMode(mode) {
                if (['discount', 'price'].includes(mode)) {
                    return;
                }
                super.setMode(mode);
            }
        };

    Registries.Component.extend(NumpadWidget, ReadOnlyNumpadWidget);
});
