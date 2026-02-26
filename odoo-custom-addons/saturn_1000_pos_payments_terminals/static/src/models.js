odoo.define('saturn_1000_pos_payments_terminals.models', function (require) {
    "use strict";

var models = require('point_of_sale.models');
var PaymentSaturn1000 = require('saturn_1000_pos_payments_terminals.payment');
models.load_fields('pos.payment.method', 'saturn_1000_payments_ways');
    models.register_payment_method('saturn_1000', PaymentSaturn1000);

    var super_order_model = models.Order.prototype;
    models.Order = models.Order.extend({

        add_paymentline: function(payment_method) {
            if (!this.pos.config.local_pc_tunneling_url){
                payment_method.payment_terminal = "";
            }
            var res = super_order_model.add_paymentline.apply(this, arguments);
            if (res.payment_method.use_payment_terminal == "saturn_1000" && this.pos.config.local_pc_tunneling_url){
                res.set_payment_status('pending');
            }
            return res;
        },

        export_as_JSON: function() {
            var json = super_order_model.export_as_JSON.apply(this,arguments);

            json.transaction_id = this.transaction_id || "";
            json.approval_code = this.approval_code || "";
            json.payment_terminal_inv_no = this.payment_terminal_inv_no || "";
            json.trace_no = this.trace_no || "";
            json.payments_terminal_id = this.payments_terminal_id || "";
            json.retrival_ref_no = this.retrival_ref_no || "";
            return json;
        },
        init_from_JSON: function(json) {
            super_order_model.init_from_JSON.apply(this,arguments);
            this.transaction_id = json.transaction_id || "";
            this.approval_code = json.approval_code || "";
            this.payment_terminal_inv_no = json.payment_terminal_inv_no || "";
            this.trace_no = json.trace_no || "";
            this.payments_terminal_id = json.payments_terminal_id || "";
            this.retrival_ref_no = json.retrival_ref_no || "";
        },


    });



});