odoo.define('product_price_checker_adv.product_price_checker', function (require) {
    "use strict";

    var AbstractAction = require('web.AbstractAction');
    var core = require('web.core');
    var QWeb = core.qweb;

    var product_price_checker = AbstractAction.extend({
        contentTemplate: "ProductPriceChecker",
        events: {
            // Keypad events
            'click .checker_button_0': function(e) { this.add_to_input(e, '0'); },
            'click .checker_button_1': function(e) { this.add_to_input(e, '1'); },
            'click .checker_button_2': function(e) { this.add_to_input(e, '2'); },
            'click .checker_button_3': function(e) { this.add_to_input(e, '3'); },
            'click .checker_button_4': function(e) { this.add_to_input(e, '4'); },
            'click .checker_button_5': function(e) { this.add_to_input(e, '5'); },
            'click .checker_button_6': function(e) { this.add_to_input(e, '6'); },
            'click .checker_button_7': function(e) { this.add_to_input(e, '7'); },
            'click .checker_button_8': function(e) { this.add_to_input(e, '8'); },
            'click .checker_button_9': function(e) { this.add_to_input(e, '9'); },
            'click .checker_button_b': function(e) { this.backspace_input(e); },
            'click .checker_button_c': function(e) { this.clear_input(e); },
            'click .checker_button_k': function(e) { this.submit_input(e); },
            'change input.checker_input': 'on_input_change',
        },
        init: function(parent, action) {
            this._super.apply(this, arguments);
        },
        start: function () {
            this.start_clock();
            this.start_focus();
            return this._super.apply(this, arguments);
        },
        start_clock: function () {
            var self = this;
            self.clock_start = setInterval(function () {
                self.$(".checker_clock").text(
                    new Date().toLocaleTimeString(navigator.language, {hour: '2-digit', minute: '2-digit', second: '2-digit'})
                );
            }, 500);
        },
        start_focus: function () {
            var self = this;
            setTimeout(function () {
                const input = self.$('.checker_input');
                const originalValue = input.val();
                input.val('').blur().focus().val(originalValue);
            }, 500);
        },
        destroy: function () {
            clearInterval(this.clock_start);
            this._super.apply(this, arguments);
        },
        add_to_input: function(e, value) {
            e.preventDefault();
            var input = this.$('.checker_input');
            input.val(input.val() + value);
        },
        backspace_input: function(e) {
            e.preventDefault();
            var input = this.$('.checker_input');
            input.val(input.val().slice(0, -1));
        },
        clear_input: function(e) {
            e.preventDefault();
            this.$('.checker_input').val('');
            this.render_html(false, '');
        },
        submit_input: function(e) {
            e.preventDefault();
            this.get_product_details();
        },
        on_input_change: function(e) {
            e.preventDefault();
            this.get_product_details();
        },
        get_product_details: function() {
            var self = this;
            var val = self.$('.checker_input').val();
            if (val) {
                self._rpc({
                    model: 'product.template',
                    method: 'get_product_details',
                    args: [val],
                }).then(function (product) {
                    self.render_html(product, val);
                }).catch(function (error) {
                    console.error("Error fetching product details:", error);
                    self.render_html(null, val);
                });
            }
        },
        render_html: function(product, val) {
            var self = this;
            if (product && product['product_id']) {
                self.product_id = product['product_id'];
                self.product_name = product['product_name'];
                self.product_description_sale = product['product_description_sale'];
                self.product_price = product['product_price'] ? parseFloat(product['product_price']).toFixed(2) : '0.00';
                self.product_barcode = product['product_barcode'];
                self.product_code = product['product_code'];
                self.product_currency_id = product['product_currency_id'];
                self.product_uom_id = product['product_uom_id'];
                self.product_pricelists = product['product_pricelists'].map(function(pricelist) {
                    pricelist.items = pricelist.items.map(function(item) {
                        item.price = parseFloat(item.price).toFixed(2); // Format price to 2 decimal places
                        return item;
                    });
                    return pricelist;
                });
            } else {
                self.product_id = '';
                self.product_name = '';
                self.product_description_sale = '';
                self.product_price = '';
                self.product_barcode = '';
                self.product_code = '';
                self.product_currency_id = '';
                self.product_uom_id = '';
                self.product_pricelists = '';
            }
            self.$el.html(QWeb.render("ProductPriceChecker", {widget: self}));
            self.start_focus();
        }
    });

    core.action_registry.add('product_price_checker', product_price_checker);
    return product_price_checker;
});
