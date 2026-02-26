odoo.define('saturn_1000_pos_payments_terminals.payment', function (require) {
"use strict";

const { Gui } = require('point_of_sale.Gui');
var core = require('web.core');
var PaymentInterface = require('point_of_sale.PaymentInterface');
var rpc = require('web.rpc');
var _t = core._t;

var PaymentSaturn1000 = PaymentInterface.extend({

    init: function () {
        this._super.apply(this, arguments);
    },

    send_payment_cancel: function () {
        this._super.apply(this, arguments);
        this.terminal.cancel();
        return Promise.resolve();
    },

    send_payment_request: async function () {
        this._super.apply(this, arguments);
        this.pos.get_order().selected_paymentline.set_payment_status('waitingCard');
        self = this;
        var receipt_name = this.pos.get_order().get_name();
        var config_id = this.pos.config.id;
        var merchantIndex = "00"
        if (self.payment_method.use_payment_terminal == "saturn_1000"){
            if (self.payment_method.saturn_1000_payments_ways=="card"){
                merchantIndex="01"
            }
            if (self.payment_method.saturn_1000_payments_ways=="e_wallet"){
                merchantIndex = "02"
            }
            if (self.payment_method.saturn_1000_payments_ways=="duitnow_qr"){
                merchantIndex="99"
            }
            if (merchantIndex){
                return rpc.query({
                    route: '/pos/payment/saturn1000/payment_request_send',
                    params: {
                        amount:this.pos.get_order().selected_paymentline.amount,
                        transactionId:receipt_name,
                        configId:config_id,
                        merchantIndex:merchantIndex
                    }
                    })
                .then(function(result){
                    if(result['success']){
                        var pos_order = self.pos.get_order()
                        Object.assign(pos_order,result.data)
                        return true;
                    }
                    else{
                        var error_str = result['error']
                        Gui.showPopup('ErrorPopup', {
                            title: _t(error_str),
                        });
                        return false;
                    }

                });
            }
        }
//        var selectionList = [
//                        {id: "01",label:"Cards Payment" ,isSelected: false,item:"01"},
//                        {id: "02",label:"Wallet",isSelected: false,item:"02"},
//                        {id: "03",label:"EPP",isSelected: false,item:"03"},
//                        {id: "99",label:"DuitNow QR",isSelected: false,item:"99"}
//                        ];
//        const { confirmed,payload } = await Gui.showPopup('SelectionPopup', {
//                        title:_t('Pay with: '),
//                        list: selectionList,
//                        confirm: (selection) => selection,
//        });
//        .then(({ confirmed, payload: selectedPaymentMethod }) => {

//        });

    },

    send_payment_reversal: function () {
        this._super.apply(this, arguments);
        this.pos.get_order().selected_paymentline.set_payment_status('reversing');
    },
});

return PaymentSaturn1000;

});
