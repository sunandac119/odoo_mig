odoo.define('pos_multi_uom_barcode.DB', function(require) {
    'use strict';
    var PosDB = require('point_of_sale.DB');
    const Registries = require('point_of_sale.Registries');

    var models = require('point_of_sale.models');
    var utils = require('web.utils');
    models.load_fields("product.product", ["barcode_uom_ids"]);

    PosDB.include({
        init: function(options){
        options = options || {};
        this.name = options.name || this.name;
        this.limit = options.limit || this.limit;

        if (options.uuid) {
            this.name = this.name + '_' + options.uuid;
        }

        //########################################################## 
        //              ORDER HISTORY DATA PREPARATION            //
        //########################################################## 
        this.order_line_by_id = this.order_line_by_id || {};
        this.order_line_by_uid = this.order_line_by_uid || {};
        this.new_order;
        this.all_order = this.all_order || [];
        this.all_display_order = this.all_display_order || [];
        this.order_by_id = this.order_by_id || {};
        this.order_by_uid = this.order_by_uid || {};
        this.all_session = this.all_session || [];
        this.all_order_temp = this.all_order_temp || [];
        //########################################################## 

        //cache the data in memory to avoid roundtrips to the localstorage
        this.cache = {};

        this.product_by_id = {};
        this.product_by_barcode = {};
        this.product_by_barcode_lines = {};
        this.product_by_category_id = {};

        this.partner_sorted = [];
        this.partner_by_id = {};
        this.partner_by_barcode = {};
        this.partner_search_string = "";
        this.partner_write_date = null;
        this.category_by_id = {};
        this.root_category_id  = 0;
        this.category_products = {};
        this.category_ancestors = {};
        this.category_childs = {};
        this.category_parent    = {};
        this.category_search_string = {};
        this.product_barcode_lines = {};
    },
    
        get_product_by_barcode: function(barcode){
            // const products = Object.this.product_by_id
            let barcodeLine = this.product_barcode_lines[barcode];
             const products = Object.values(this.product_by_id)
            // let product = products.find(l => l.product_tmpl_id === barcodeLine.product_id[0]);
            let product = products.find(l => l.barcode === barcodeLine.barcode);
            if(barcodeLine){
                product.lst_price = barcodeLine.sale_price;
                product.uom_id = barcodeLine.uom_id;
                return product;
            }
            // debugger;
        },

// ###################################################################################
//          BELOW IS THE CODE FOR THE ORDER HISTORY LINES AND RECIEPT CODE          //
// ###################################################################################
        all_sessions: function (all_session) {
            this.all_session = all_session;
        },
        all_orders: function (all_order) {
            var self = this;
            var new_write_date = "";
            for (var i = 0, len = all_order.length; i < len; i++) {
                var each_order = all_order[i];
                if (!this.order_by_id[each_order.id]) {
                    this.all_order.push(each_order);
                    this.all_order_temp.push(each_order);
                    this.order_by_id[each_order.id] = each_order;
                    this.order_by_uid[each_order.sh_uid] = each_order;
                }
            }
        },
        all_orders_line: function (all_order_line) {
            var new_write_date = "";
            for (var i = 0, len = all_order_line.length; i < len; i++) {
                var each_order_line = all_order_line[i];
                this.order_line_by_id[each_order_line.id] = each_order_line;
                this.order_line_by_uid[each_order_line.sh_line_id] = each_order_line;
            }
        },
        add_products: function(products){
            var stored_categories = this.product_by_category_id;

            if(!products instanceof Array){
                products = [products];
            }
            for(var i = 0, len = products.length; i < len; i++){
                var product = products[i];
                if (product.id in this.product_by_id) continue;
                if (product.available_in_pos){
                    var search_string = utils.unaccent(this._product_search_string(product));
                    var categ_id = product.pos_categ_id ? product.pos_categ_id[0] : this.root_category_id;
                    product.product_tmpl_id = product.product_tmpl_id[0];
                    if(!stored_categories[categ_id]){
                        stored_categories[categ_id] = [];
                    }
                    stored_categories[categ_id].push(product.id);

                    if(this.category_search_string[categ_id] === undefined){
                        this.category_search_string[categ_id] = '';
                    }
                    this.category_search_string[categ_id] += search_string;

                    var ancestors = this.get_category_ancestors_ids(categ_id) || [];

                    for(var j = 0, jlen = ancestors.length; j < jlen; j++){
                        var ancestor = ancestors[j];
                        if(! stored_categories[ancestor]){
                            stored_categories[ancestor] = [];
                        }
                        stored_categories[ancestor].push(product.id);

                        if( this.category_search_string[ancestor] === undefined){
                            this.category_search_string[ancestor] = '';
                        }
                        this.category_search_string[ancestor] += search_string;
                    }
                }
                this.product_by_id[product.id] = product;
                if(product.barcode){
                    this.product_by_barcode[product.barcode] = product;
                }
                if(product.barcode_lines){
                   for(var i = 0; i < product.barcode_lines.length; i++){
                    this.product_by_barcode_lines[product.barcode_lines[i].barcode] =
                    {
                        'product':product,
                        'price':product.barcode_lines[i].sale_price,
                        'uom_id':product.barcode_lines[i].uom_id,
                     };
                   }
                }
            }
        },
// #############################################################################################

    })

    return PosDB;
});
