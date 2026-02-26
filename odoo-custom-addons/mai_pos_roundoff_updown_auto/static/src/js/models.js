odoo.define('mai_pos_roundoff_updown_auto.models', function (require) {
    "use strict";

    var models = require('point_of_sale.models');
    var core = require('web.core');
    var _t = core._t;
    var utils = require('web.utils');

    var round_pr = utils.round_precision;

    function decimalAdjust(value){
        var split_value = value.toFixed(2).split('.');
        //convert string value to integer
        for(var i=0; i < split_value.length; i++){
            split_value[i] = parseInt(split_value[i]);
        }
        var reminder_value = split_value[1] % 10;
        var division_value = parseInt(split_value[1] / 10);
        var rounding_value;
        var nagative_sign = false;
        if(split_value[0] == 0 && value < 0){
            nagative_sign = true;
        }
        if(_.contains(_.range(0,3), reminder_value)){
            rounding_value = eval(split_value[0].toString() + '.' + division_value.toString() + '0' )
        }else if(_.contains(_.range(3,5), reminder_value)){
            rounding_value = eval(split_value[0].toString() + '.' + division_value.toString() + '5' )
        }else if(_.contains(_.range(5,8), reminder_value)){
            rounding_value = eval(split_value[0].toString() + '.' + division_value.toString() + '5' )
        }else if(_.contains(_.range(8,10), reminder_value)){
            if(split_value[1] == 98 || split_value[1] == 99){
                rounding_value = Math.round(value)
            } else{
                division_value = division_value + 1;
                rounding_value = eval(split_value[0].toString() + '.' + division_value.toString() + '0' )
            }
        }
        if(nagative_sign){
            return -rounding_value;
        }else{
            return rounding_value;
        }
    }

    var _super_Order = models.Order.prototype;
    models.Order = models.Order.extend({
        initialize: function(attributes,options){
            if(options.json){
                options.json.lines = [];
                options.json.statement_ids = [];
            }
            _super_Order.initialize.apply(this, arguments);
            this.set({
                ret_o_id:       null,
                ret_o_ref:      null,
                sale_mode:      true,
                missing_mode:   false,
            });
            $("div#sale_mode").addClass('selected-menu');
            $("div#order_return").removeClass('selected-menu');
            this.receipt_type = 'receipt';  // 'receipt' || 'invoice'
            this.temporary = options.temporary || false;
            this.rounding_status = false;
            return this;
        },
        //Rounding
        set_rounding_status: function(rounding_status) {
            this.rounding_status = rounding_status
        },
        get_rounding_status: function() {
            return this.rounding_status;
        },
        getNetTotalTaxIncluded: function() {
            var total = this.get_total_with_tax();
            if(this.get_rounding_status()){
                if(this.pos.config.enable_rounding && this.pos.config.rounding_options == 'digits'){
                    var value = round_pr(Math.max(0,total))//decimalAdjust(total);
                    return value;
                }else if(this.pos.config.enable_rounding && this.pos.config.rounding_options == 'points'){
                    var total = this.get_total_without_tax() + this.get_total_tax();
                    var value = decimalAdjust(total);
                    return value;
                }
            }else {
                return total
            }
        },
        get_rounding : function(){
            if(this.get_rounding_status()){
                var total = this ? this.get_total_with_tax() : 0;
                var rounding = this ? this.getNetTotalTaxIncluded() - total: 0;
                return rounding;
            }
        },
        get_due: function(paymentline) {
            if (!paymentline) {
                var due = this.getNetTotalTaxIncluded() - this.get_total_paid();
            } else {
                var due = this.getNetTotalTaxIncluded();
                var lines = this.paymentlines.models;
                for (var i = 0; i < lines.length; i++) {
                    if (lines[i] === paymentline) {
                        break;
                    } else {
                        due -= lines[i].get_amount();
                    }
                }
            }
            return round_pr(Math.max(0,due), this.pos.currency.rounding);
        },
        get_change: function(paymentline) {
            if (!paymentline) {
                var change = this.get_total_paid() - this.getNetTotalTaxIncluded();
            } else {
                var change = -this.getNetTotalTaxIncluded();
                var lines  = this.paymentlines.models;
                for (var i = 0; i < lines.length; i++) {
                    change += lines[i].get_amount();
                    if (lines[i] === paymentline) {
                        break;
                    }
                }
            }
            return round_pr(Math.max(0,change), this.pos.currency.rounding);
        },
        export_as_JSON: function() {
            var orders = _super_Order.export_as_JSON.call(this);
            var new_val = {
                rounding: this.get_rounding(),
                is_rounding: this.pos.config.enable_rounding,
                rounding_option: this.pos.config.enable_rounding ? this.pos.config.rounding_options : false,
            }
            $.extend(orders, new_val);
            return orders;
        },
        export_for_printing: function(){
            var orders = _super_Order.export_for_printing.call(this);
            var order_no = this.get_name() || false ;
            var order_no = order_no ? this.get_name().replace(_t('Order '),'') : false;
            var new_val = {
                date_order: this.get_date_order() || false,
                rounding: this.get_rounding(),
                net_amount: this.getNetTotalTaxIncluded(),
            };
            $.extend(orders, new_val);
            return orders;
        },
        set_date_order: function(val){
            this.set('date_order',val)
        },
        get_date_order: function(){
            return this.get('date_order')
        },
    });
});