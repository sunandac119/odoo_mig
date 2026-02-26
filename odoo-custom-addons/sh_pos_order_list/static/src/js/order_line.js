odoo.define("sh_pos_order_list.order_line", function (require) {
    "use strict";

    const { debounce } = owl.utils;
    const PosComponent = require("point_of_sale.PosComponent");
    const Registries = require("point_of_sale.Registries");
    const { useListener } = require("web.custom_hooks");
    const rpc = require("web.rpc");
    var core = require("web.core");
    var framework = require("web.framework");
    var QWeb = core.qweb;

    class TemplatePosOrderLine extends PosComponent {
        constructor() {
            super(...arguments);
        }
        get highlight() {
            return this.props.service_order !== this.props.selectedQuotation ? "" : "highlight";
        }
    }
    TemplatePosOrderLine.template = "TemplatePosOrderLine";
    Registries.Component.add(TemplatePosOrderLine);

    return TemplatePosOrderLine;
});
