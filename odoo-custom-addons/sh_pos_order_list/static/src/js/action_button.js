odoo.define("sh_pos_order_list.action_button", function (require) {
    "use strict";

    const PosComponent = require("point_of_sale.PosComponent");
    const { useListener } = require("web.custom_hooks");
    const Registries = require("point_of_sale.Registries");
    const ProductScreen = require("point_of_sale.ProductScreen");
    const rpc = require("web.rpc");

    class OrderHistoryButton extends PosComponent {
        constructor() {
            super(...arguments);
            useListener("click-order-history-button", this.onClickOrderHistoryButton);
        }
        onClickOrderHistoryButton() {
            var self = this;
            const { confirmed, payload } = self.showTempScreen("OrderListScreen");
            if (confirmed) {
            }
        }
    }
    OrderHistoryButton.template = "OrderHistoryButton";
    ProductScreen.addControlButton({
        component: OrderHistoryButton,
        condition: function () {
            return this.env.pos.config.sh_enable_order_list;
        },
    });
    Registries.Component.add(OrderHistoryButton);

    return OrderHistoryButton;
});
