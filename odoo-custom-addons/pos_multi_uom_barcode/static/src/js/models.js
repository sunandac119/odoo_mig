odoo.define('pos_multi_uom_barcode.models', function (require) {
    "use strict";

    var models = require('point_of_sale.models');
    var core = require('web.core');
    var rpc = require('web.rpc');
    var _t = core._t;
    var posmodel_super = models.PosModel.prototype;
    models.load_fields('product.product', 'barcode_uom_ids');

    // Load barcode UOMs
    models.load_models([{
        model: 'product.barcode.uom',
            fields: ['id', 'uom_id', 'barcode', 'sale_price', 'product_id'],
            loaded: function(self, barcode_lines){
            var barcode_line_by_id = {};
            var barcode_line_by_barcode = {};
            _.each(barcode_lines, function (line) {
                barcode_line_by_id[line.id] = line;
                barcode_line_by_barcode[line.barcode] = line;
            });
             self.barcode_lines = barcode_lines;
             self.db.product_barcode_lines = barcode_line_by_barcode;
        },
    }]);


    var existing_models = models.PosModel.prototype.models;
      var product_index = _.findIndex(existing_models, function (model) {
          return model.model === "product.product";
      });
      var product_model = existing_models[product_index];

      models.load_models([{
        model:  product_model.model,
        fields: product_model.fields,
        order:  product_model.order,
        domain: product_model.domain,
        context: product_model.context,
        loaded: function(self, products){
            var using_company_currency = self.config.currency_id[0] === self.company.currency_id[0];
            var conversion_rate = self.currency.rate / self.company_currency.rate;
            self.db.add_products(_.map(products, function (product) {
                if (!using_company_currency) {
                    product.lst_price = round_pr(product.lst_price * conversion_rate, self.currency.rounding);
                }
                product.categ = _.findWhere(self.product_categories, {'id': product.categ_id[0]});
                product.barcode_lines = [];
                if (product.barcode_uom_ids && product.barcode_uom_ids.length) {
                    for(var i = 0; i < product.barcode_uom_ids.length; i++) {
                        var line = _.findWhere(self.barcode_lines, {'id': product.barcode_uom_ids[i]});
                        if (line) {
                            product.barcode_lines.push(line);
                        }
                    }
                }
                product.pos = self;
                return new models.Product({}, product);
            }));
        },
    }])



    // models.PosModel = models.PosModel.extend({
    //     load_server_data: function () {
    //         var self = this;
    //         return posmodel_super.load_server_data.apply(this, arguments).then(function () {
    //             var product_model = {
    //                 model:  'product.product',
    //                 fields: ['display_name', 'lst_price', 'standard_price', 'categ_id', 'pos_categ_id', 'taxes_id',
    //                          'barcode', 'default_code', 'to_weight', 'uom_id', 'description_sale', 'description',
    //                          'product_tmpl_id','tracking', 'write_date', 'available_in_pos', 'attribute_line_ids','active','barcode_uom_ids'],
    //                 order:  _.map(['sequence','default_code','name'], function (name) { return {name: name}; }),
    //                 domain: function(self){
    //                     var domain = ['&', '&', ['sale_ok','=',true],['available_in_pos','=',true],
    //                                   '|',['company_id','=',self.config.company_id[0]],['company_id','=',false]];
    //                     if (self.config.limit_categories &&  self.config.iface_available_categ_ids.length) {
    //                         domain.unshift('&');
    //                         domain.push(['pos_categ_id', 'in', self.config.iface_available_categ_ids]);
    //                     }
    //                     if (self.config.iface_tipproduct){
    //                       domain.unshift(['id', '=', self.config.tip_product_id[0]]);
    //                       domain.unshift('|');
    //                     }
    //                     return domain;
    //                 },
    //                 context: function(self){ return { display_default_code: false }; },
    //                 loaded: function(self, products){
    //                     var using_company_currency = self.config.currency_id[0] === self.company.currency_id[0];
    //                     var conversion_rate = self.currency.rate / self.company_currency.rate;
    //                     self.db.add_products(_.map(products, function (product) {
    //                         if (!using_company_currency) {
    //                             product.lst_price = round_pr(product.lst_price * conversion_rate, self.currency.rounding);
    //                         }
    //                         product.categ = _.findWhere(self.product_categories, {'id': product.categ_id[0]});
    //                         product.barcode_lines = [];
    //                         console.log('\n\n\n\n product',product)
    //                         if (product.barcode_uom_ids && product.barcode_uom_ids.length) {
    //                             for(var i = 0; i < product.barcode_uom_ids.length; i++) {
    //                                 var line = _.findWhere(self.barcode_lines, {'id': product.barcode_uom_ids[i]});
    //                                 if (line) {
    //                                     product.barcode_lines.push(line);
    //                                 }
    //                             }
    //                         }
    //                         product.pos = self;
    //                         return new models.Product({}, product);
    //                     }));
    //                 },
    //             };

    //             return rpc.query({
    //                 model: product_model.model,
    //                 method: 'search_read',
    //                 args: [product_model.domain(self), product_model.fields],
    //                 context: product_model.context(self),
    //             }).then(function(products){
    //                 product_model.loaded(self, products);
    //             });
    //         });
    //     },
    // });
});
