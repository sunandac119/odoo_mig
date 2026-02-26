odoo.define('pos_multi_uom_barcode.models', function (require) {
    "use strict";

    var models = require('point_of_sale.models');
    var core = require('web.core');
    var rpc = require('web.rpc');
    var _t = core._t;
    var BarcodeParser = require('barcodes.BarcodeParser');
    var posmodel_super = models.PosModel.prototype;
    var exports = models;

    // Load product.barcode.uom model
    models.load_models([{
        model: 'product.barcode.uom',
        fields: ['id', 'uom_id', 'barcode', 'sale_price'],
        loaded: function(self, barcode_lines){
            var barcode_line_by_id = {};
            _.each(barcode_lines, function (line) {
                barcode_line_by_id[line.id] = line;
            });
            self.barcode_lines = barcode_lines;
        },
    }]);

    // Extend PosModel
    exports.PosModel = exports.PosModel.extend({
        // TOFIX; overriding modules here prevents multi cashier selection
        models: [
            {
                model:  'product.product',
                fields: ['display_name', 'lst_price', 'standard_price', 'categ_id', 'pos_categ_id', 'taxes_id',
                         'barcode', 'default_code', 'to_weight', 'uom_id', 'description_sale', 'description',
                         'product_tmpl_id','tracking', 'write_date', 'available_in_pos', 'attribute_line_ids','active'],
                order:  _.map(['sequence','default_code','name'], function (name) { return {name: name}; }),
                domain: function(self){
                    var domain = ['&', '&', ['sale_ok','=',true],['available_in_pos','=',true],'|',['company_id','=',self.config.company_id[0]],['company_id','=',false]];
                    if (self.config.limit_categories &&  self.config.iface_available_categ_ids.length) {
                        domain.unshift('&');
                        domain.push(['pos_categ_id', 'in', self.config.iface_available_categ_ids]);
                    }
                    if (self.config.iface_tipproduct){
                        domain.unshift(['id', '=', self.config.tip_product_id[0]]);
                        domain.unshift('|');
                    }
                    return domain;
                },
                context: function(self){ return { display_default_code: false }; },
                loaded: function(self, products){
                    var using_company_currency = self.config.currency_id[0] === self.company.currency_id[0];
                    var conversion_rate = self.currency.rate / self.company_currency.rate;
                    self.db.add_products(_.map(products, function (product) {
                        if (!using_company_currency) {
                            product.lst_price = round_pr(product.lst_price * conversion_rate, self.currency.rounding);
                        }
                        product.categ = _.findWhere(self.product_categories, {'id': product.categ_id[0]});
                        product.barcode_lines = [];
                        for(var i = 0; i < product.barcode_uom_ids.length; i++)
                        {
                            product.barcode_lines.push(_.findWhere(self.barcode_lines, {'id': product.barcode_uom_ids[i]}));
                        }

                        product.pos = self;
                        return new exports.Product({}, product);
                    }));
                },
            },
        ],
    });

});
