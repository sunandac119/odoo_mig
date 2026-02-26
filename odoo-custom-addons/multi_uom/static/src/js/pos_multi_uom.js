
odoo.define('multi_uom.pos_multi_uom', function (require) {
    "use strict";

    const models = require('point_of_sale.models');
    const _super_posmodel = models.PosModel.prototype;

    models.load_models([{
        model: 'product.uom.mapping',
        fields: ['product_tmpl_id', 'uom_id', 'factor', 'barcode', 'price'],
        loaded: function (self, uom_mappings) {
            self.uom_mappings = uom_mappings;
        }
    }]);

    models.PosModel = models.PosModel.extend({
        scan_product: function (parsed_code) {
            const mapping = this.uom_mappings.find(m => m.barcode === parsed_code.code);
            if (mapping) {
                const product = this.db.get_product_by_template_id(mapping.product_tmpl_id[0]);
                if (product) {
                    const order = this.get_order();
                    return order.add_product(product, {
                        price: mapping.price,
                        quantity: mapping.factor,
                    });
                }
            }
            return _super_posmodel.scan_product.apply(this, arguments);
        }
    });
});
