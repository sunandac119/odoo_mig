odoo.define('bi_pos_packaging_barcode.db', function(require) {
    "use strict";
    
    var PosDB = require('point_of_sale.DB');
    
    var models = require('point_of_sale.models');
    console.log("called=============");
    models.load_models([
    {
        model: 'product.packaging',
        fields: ['name','barcode','product_id','qty'],
        domain: function(self){return [['barcode', '!=', '']]; },
        loaded: function(self,product_packagings){
            self.db.add_packagings(product_packagings);
        },
    }],{'after': 'product.product'});
    
    PosDB.DB = PosDB.include({

        init: function(options){ 
            this.product_packaging_by_barcode = {};
            this._super(options);
        },

        add_packagings: function(product_packagings){
            var self = this;
            _.map(product_packagings, function (product_packaging) {
                if (_.find(self.product_by_id, {'id': product_packaging.product_id[0]})) {
                    self.product_packaging_by_barcode[product_packaging.barcode] = product_packaging;
                }
            });
        },
        get_product_by_barcode: function(barcode) {
            if (this.product_by_barcode[barcode]) {
                return this.product_by_barcode[barcode];
            } else if (this.product_packaging_by_barcode[barcode]) {
                var packaging = this.product_packaging_by_barcode[barcode];
                var product = this.product_by_id[packaging.product_id[0]];
                product.display_name = packaging.name; // Set packaging name as the display name
                product.list_price = packaging.list_price; // Set packaging price as the list price
                return product;
            }
            return undefined;
        },

    })

});
