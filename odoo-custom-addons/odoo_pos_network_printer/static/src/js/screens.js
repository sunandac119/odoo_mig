/* Copyright (c) 2016-Present Webkul Software Pvt. Ltd. (<https://webkul.com/>) */
/* See LICENSE file for full copyright and licensing details. */
/* License URL : <https://store.webkul.com/license.html/> */
odoo.define('odoo_pos_network_printer.screens', function (require) {
    "use strict";
    const ReceiptScreen = require('point_of_sale.ReceiptScreen');
    const Registries = require('point_of_sale.Registries');
    var core = require('web.core');
    var QWeb = core.qweb;
    var rpc = require('web.rpc')
    var _t      = core._t;

    const PosResReceiptScreen = (ReceiptScreen) =>
        class extends ReceiptScreen{
            printNetworkPrinterReceipt(event){
                var self = this;
                var OrderReceiptEnv = self.env.pos.get_order().getOrderReceiptEnv()
                OrderReceiptEnv.env = self.env
                OrderReceiptEnv.pos = self.env.pos
                var receipt = QWeb.render('XmlReceipt', OrderReceiptEnv);
                // console.log("receipt",receipt)
                rpc.query({
                    model:'pos.order',
                    method:'get_esc_command_set',
                    args:[{"data":receipt}]
                })
                .catch(function(unused, event){
                    event.preventDefault();
                    self.gui.show_popup('error',{
                        title: _t('Failed To Fetch Receipt Details.'),
                        body:  _t('Please make sure you are connected to the network.'),
                    });
                })
                .then(function(esc_commands){
                    var esc = esc_commands.replace("\n", "\x0A")
                    var printer_name = self.env.pos.config.printer_name;
                    if(! qz.websocket.isActive()){
                        self.env.pos.connect_to_nw_printer().finally(function(){
                            if(self.env.pos.nw_printer && self.env.pos.nw_printer.remote_status == "success"){
                                var config = qz.configs.create(printer_name);
                                var data = [esc]
                                // { type: 'raw', format: 'image', data: receipt_data.receipt.company.logo, options: { language: "ESCPOS", dotDensity: 'double'} },
                                qz.print(config, data).then(function() {}).catch(function(e){
                                    console.error(e);
                                });
                            }
                        })
                    }else{
                        var config = qz.configs.create(printer_name);
                        var data = [esc]
                        // { type: 'raw', format: 'image', data: receipt_data.receipt.company.logo, options: { language: "ESCPOS", dotDensity: 'double'} },
                        qz.print(config, data).then(function() {});
                    }
                });
            }
            mounted(){
                super.mounted();
                this.printNetworkPrinterReceipt();
            }	
        }
	Registries.Component.extend(ReceiptScreen, PosResReceiptScreen);
});