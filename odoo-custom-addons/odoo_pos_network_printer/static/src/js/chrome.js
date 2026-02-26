/* Copyright (c) 2016-Present Webkul Software Pvt. Ltd. (<https://webkul.com/>) */
/* See LICENSE file for full copyright and licensing details. */
/* License URL : <https://store.webkul.com/license.html/> */

odoo.define('odoo_pos_network_printer.chrome', function (require) {
    "use strict";
    const PosComponent = require('point_of_sale.PosComponent');
    const Registries = require('point_of_sale.Registries');

    class SynchNetworkPrinterWidget extends PosComponent {
        mounted() {
            super.mounted()
            this.onClick();
        }
        onClick() {
            var self = this;
            self.env.pos.nw_printer.disconnect_from_printer().finally(function(e){
                self.env.pos.nw_printer.connect_to_printer();
            })
        }
    }
    SynchNetworkPrinterWidget.template = 'SynchNetworkPrinterWidget';
    Registries.Component.add(SynchNetworkPrinterWidget);
    return SynchNetworkPrinterWidget;
});