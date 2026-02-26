odoo.define('pos_loyalty_reward_control.refresh_button', function (require) {
'use strict';

const PosComponent = require('point_of_sale.PosComponent');
const ProductScreen = require('point_of_sale.ProductScreen');
const Registries = require('point_of_sale.Registries');

class RefreshPosButton extends PosComponent {
    async onClick() {
        try {
            const { confirmed } = await this.showPopup('ConfirmPopup', {
                title: 'Refresh POS Data',
                body: 'Reload latest Products and Members?',
            });
            if (!confirmed) return;

            this.showPopup('LoadingPopup', {
                title: 'Refreshing',
                body: 'Updating products & members...',
            });

            const pos = this.env.pos;

            const products = await pos.env.services.rpc({
                model: 'product.product',
                method: 'search_read',
                args: [[]],
            });
            pos.db.add_products(products);

            const partners = await pos.env.services.rpc({
                model: 'res.partner',
                method: 'search_read',
                args: [[]],
            });
            pos.db.add_partners(partners);

            this.showPopup('ConfirmPopup', {
                title: 'Done',
                body: 'POS data refreshed successfully',
            });
        } catch (e) {
            this.showPopup('ErrorPopup', {
                title: 'Refresh Failed',
                body: e.message,
            });
        }
    }
}

RefreshPosButton.template = 'RefreshPosButton';

ProductScreen.addControlButton({
    component: RefreshPosButton,
    condition: () => true,
});

Registries.Component.add(RefreshPosButton);
});
