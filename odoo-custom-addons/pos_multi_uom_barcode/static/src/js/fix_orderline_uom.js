odoo.define('pos_multi_uom_barcode.FixQtyChangeUoM', function(require) {
    'use strict';

    const models = require('point_of_sale.models');
    const ProductScreen = require('point_of_sale.ProductScreen');
    const Registries = require('point_of_sale.Registries');

    // --- PATCH ORDERLINE ---
    const _super_orderline = models.Orderline.prototype;
    models.Orderline = models.Orderline.extend({
        initialize: function(attr, options) {
            _super_orderline.initialize.call(this, attr, options);
            // Default to product's base UoM if none is set
            this.product_uom_id = this.product_uom_id || this.product.uom_id;
        },
        init_from_JSON: function(json) {
            _super_orderline.init_from_JSON.apply(this, arguments);
            this.product_uom_id = json.product_uom_id;
        },
        export_as_JSON: function() {
            const json = _super_orderline.export_as_JSON.call(this);
            json.product_uom_id = this.product_uom_id;
            return json;
        },
        set_custom_uom_id: function(uom) {
            this.product_uom_id = uom;
            this.trigger('change', this);
        },
        get_unit: function() {
            // 🔑 Always respect product_uom_id if set
            if (this.product_uom_id) {
                const uom_id = Array.isArray(this.product_uom_id)
                    ? this.product_uom_id[0]
                    : this.product_uom_id;
                return this.pos.units_by_id[uom_id];
            }
            return _super_orderline.get_unit.call(this);
        },
    });

    // --- PATCH PRODUCTSCREEN BARCODE ACTION ---
    const PosFrProductScreen = ProductScreen => class extends ProductScreen {
        _barcodeProductAction(code) {
            if (!this.env.pos.scan_product(code)) {
                this._barcodeErrorAction(code);
            }
            const order = this.env.pos.get_order();
            const order_line = order && order.get_selected_orderline();
            if (!order_line) return;

            const product = order_line.get_product();
            if (product && Array.isArray(product.barcode_lines)) {
                for (let line of product.barcode_lines) {
                    if (code.base_code === line.barcode) {
                        const uom = this.env.pos.units_by_id[line.uom_id[0]];
                        if (uom) {
                            // ✅ Lock UoM on orderline
                            order_line.set_custom_uom_id([uom.id, uom.name]);
                            order_line.product.temp_uom_id = uom.id;
                            // Recompute price under this UoM
                            order_line.set_unit_price(
                                order_line.product.get_price(
                                    order_line.order.pricelist,
                                    order_line.get_quantity()
                                )
                            );
                            delete order_line.product.temp_uom_id;
                        }
                        break;
                    }
                }
            }
        }
    };

    Registries.Component.extend(ProductScreen, PosFrProductScreen);

    return ProductScreen;
});
