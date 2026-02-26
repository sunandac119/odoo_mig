odoo.define('product_add_to_cart_ajax_av.website_sale_frontend', function (require) {
'use strict';
	var publicWidget = require('web.public.widget');
	const ajax = require('web.ajax');
	var wSaleUtils = require('website_sale.utils');
	var WebsiteSale = require('website_sale.website_sale');

	publicWidget.registry.WebsiteSale.include({
	    _onClickAdd: function (ev) {
	        ev.preventDefault();
	        var self = this;
	        var $form = $(ev.currentTarget).closest('form');
	        if ($(ev.currentTarget).attr('data-value') == 'True'){
	        	ajax.jsonRpc("/shop/cart/update_json", 'call', {
                	'product_id':parseInt($form.find('input[name="product_id"]').val()),
	                'add_qty': parseFloat($form.find('input[name="add_qty"]').val() || 1),
	            }).then(function(data){
	            	wSaleUtils.updateCartNavBar(data);
	            	var $navButton = $('header .o_wsale_my_cart').first();
		            var animation = wSaleUtils.animateClone($navButton, $(ev.currentTarget).parents('.oe_product'), 25, 40);
	            });
	        }
	       	else{
	       		this.isBuyNow = $(ev.currentTarget).attr('id') === 'buy_now';
	        	return this._handleAdd($form);
	       	}
	    },

	});
});