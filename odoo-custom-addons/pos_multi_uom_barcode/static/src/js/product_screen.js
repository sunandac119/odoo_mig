odoo.define('pos_multi_uom_barcode.ProductScreen', function(require) {
    'use strict';

    const ProductScreen = require('point_of_sale.ProductScreen');
    const Registries = require('point_of_sale.Registries');

    const PosFrProductScreen = ProductScreen => class extends ProductScreen {

        _barcodeProductAction(code) {

            if (!this.env.pos.scan_product(code)) {
                this._barcodeErrorAction(code);
            }

            const order = this.env.pos.get_order();
            const pricelist = order?.pricelist;
            const order_line = order?.selected_orderline;
            const product = order_line?.get_product();

            if (product && order_line) {

                if (Array.isArray(product.uom_id)) {
                    order_line.product_uom_id = [...product.uom_id];
                } else {
                    const unit = this.env.pos.units_by_id[product.uom_id];
                    order_line.product_uom_id = [unit.id, unit.name];
                }

                const computed_price = product.get_price(pricelist, order_line.get_quantity());
                order_line.set_unit_price(computed_price);
            }

            // Multi-UOM barcode matching
            for (let unit of this.env.pos.units) {
                if (product && Array.isArray(product.barcode_lines)) {
                    for (let line of product.barcode_lines) {
                        if (code.base_code === line.barcode && line.uom_id[0] === unit.id) {

                            order_line.product_uom_id = [unit.id, unit.name];
                            order_line.product.temp_uom_id = unit.id;

                            const updated_price = product.get_price(pricelist, order_line.get_quantity());
                            order_line.set_unit_price(updated_price);
                            break;
                        }
                    }
                }
            }
        }

        async _updateSelectedOrderline(event) {

            const order = this.env.pos.get_order();
            const pricelist = order?.pricelist;
            const selectedLine = order?.get_selected_orderline();

            if (!selectedLine) return;


            if (Array.isArray(selectedLine.product_uom_id) && selectedLine.product_uom_id.length) {
                selectedLine.product.temp_uom_id = selectedLine.product_uom_id[0];
            } else if (selectedLine.product_uom_id) {
                selectedLine.product.temp_uom_id = parseInt(selectedLine.product_uom_id);
            }

            if (this.state.numpadMode === 'quantity' && this.env.pos.disallowLineQuantityChange()) {

                const lastId = order.orderlines.last().cid;
                const currentQuantity = selectedLine.get_quantity();
                const parsedInput = event.detail.buffer ? parseFloat(event.detail.buffer) : 0;


                if (lastId !== selectedLine.cid) {
                    this._showDecreaseQuantityPopup();
                } else {
                    this._setValue(event.detail.buffer);
                }

            } else {

                const { buffer } = event.detail;
                const val = buffer === null ? 'remove' : buffer;

                this._setValue(val);

                const recalculated_price = selectedLine.product.get_price(pricelist, selectedLine.get_quantity());

                selectedLine.set_unit_price(recalculated_price);
            }

            delete selectedLine.product.temp_uom_id;

               
        }
    };

    Registries.Component.extend(ProductScreen, PosFrProductScreen);
    return ProductScreen;
});

// odoo.define('pos_multi_uom_barcode.ProductScreen', function(require) {
//     'use strict';

//     const ProductScreen = require('point_of_sale.ProductScreen');
//     const Registries = require('point_of_sale.Registries');


//     const PosFrProductScreen = ProductScreen => class extends ProductScreen {
//         _barcodeProductAction(code) {
//             // NOTE: scan_product call has side effect in pos if it returned true.
//             if (!this.env.pos.scan_product(code)) {
//                 this._barcodeErrorAction(code);
//             }
//             const order = this.env.pos.get_order();
//             if(order) {
//                 const order_line = order.selected_orderline
//                 const product = order_line.get_product();
//                 if (product && order_line) {
//                     if (Array.isArray(product.uom_id)) {
//                         order_line.product_uom_id = [product.uom_id[0], product.uom_id[1]];
//                     } else {
//                         // fallback if it's just an ID
//                         const unit = this.env.pos.units_by_id[product.uom_id];
//                         order_line.product_uom_id = [unit.id, unit.name];
//                     }

//                     // order_line.product_uom_id = [unit.id, unit.name];
//                     // order_line.product.temp_uom_id = unit.id;
//                     order_line.set_unit_price(
//                         order_line.product.get_price(order_line.order.pricelist, order_line.get_quantity())
//                     );
//                 }
//                 for (let unit of this.env.pos.units) {
//                     if (product && Array.isArray(product.barcode_lines)) {
//                         for (let line of product.barcode_lines) {
//                             if (code.base_code === line.barcode && line.uom_id[0] === unit.id) {
//                                 order_line.product_uom_id = [unit.id, unit.name];
//                                 order_line.product.temp_uom_id = unit.id;
//                                 order_line.set_unit_price(
//                                     order_line.product.get_price(order_line.order.pricelist, order_line.get_quantity())
//                                 );
//                                 break;
//                             }
//                         }
//                     }
//                 }
//             }
//         }
// #################################################
//         // async _updateSelectedOrderline(event) {
//         //     if(this.state.numpadMode === 'quantity' && this.env.pos.disallowLineQuantityChange()) {
//         //         let order = this.env.pos.get_order();
//         //         let selectedLine = order.get_selected_orderline();
//         //         if (selectedLine.product_uom_id[0]){
//         //             selectedLine.product.temp_uom_id = selectedLine.product_uom_id[0]
//         //         }
//         //         else{
//         //             selectedLine.product.temp_uom_id = parseInt(selectedLine.product_uom_id)
//         //         }
//         //         let lastId = order.orderlines.last().cid;
//         //         let currentQuantity = this.env.pos.get_order().get_selected_orderline().get_quantity();

//         //         if(selectedLine.noDecrease) {
//         //             this.showPopup('ErrorPopup', {
//         //                 title: this.env._t('Invalid action'),
//         //                 body: this.env._t('You are not allowed to change this quantity'),
//         //             });
//         //             return;
//         //         }
//         //         const parsedInput = event.detail.buffer && parse.float(event.detail.buffer) || 0;
//         //         if(lastId != selectedLine.cid)
//         //             this._showDecreaseQuantityPopup();
//         //         else if(currentQuantity < parsedInput)
//         //             this._setValue(event.detail.buffer);
//         //         else if(parsedInput < currentQuantity)
//         //             this._showDecreaseQuantityPopup();
//         //     } else {
//         //         let order = this.env.pos.get_order();
//         //         let selectedLine = order.get_selected_orderline();
//         //         if (selectedLine.product_uom_id[0]){
//         //             selectedLine.product.temp_uom_id = selectedLine.product_uom_id[0]
//         //         }
//         //         else{
//         //             selectedLine.product.temp_uom_id = parseInt(selectedLine.product_uom_id)
//         //         }
//         //         let { buffer } = event.detail;
//         //         let val = buffer === null ? 'remove' : buffer;
//         //         this._setValue(val);
//         //         delete selectedLine.product.temp_uom_id;
//         //     }
//         // }
// #####################################################################
//         async _updateSelectedOrderline(event) {
//             const order = this.env.pos.get_order();
//             const selectedLine = order?.get_selected_orderline();
//             if (!selectedLine) return;

//             // Normalize temp_uom_id
//             if (Array.isArray(selectedLine.product_uom_id) && selectedLine.product_uom_id.length) {
//                 selectedLine.product.temp_uom_id = selectedLine.product_uom_id[0];
//             } else if (selectedLine.product_uom_id) {
//                 selectedLine.product.temp_uom_id = parseInt(selectedLine.product_uom_id);
//             }

//             if (this.state.numpadMode === 'quantity' && this.env.pos.disallowLineQuantityChange()) {
//                 const lastId = order.orderlines.last().cid;
//                 const currentQuantity = selectedLine.get_quantity();

//                 if (selectedLine.noDecrease) {
//                     this.showPopup('ErrorPopup', {
//                         title: this.env._t('Invalid action'),
//                         body: this.env._t('You are not allowed to change this quantity'),
//                     });
//                     return;
//                 }

//                 const parsedInput = event.detail.buffer ? parseFloat(event.detail.buffer) : 0;

//                 if (lastId !== selectedLine.cid) {
//                     this._showDecreaseQuantityPopup();
//                 } else if (currentQuantity < parsedInput) {
//                     this._setValue(event.detail.buffer);
//                 } else if (parsedInput < currentQuantity) {
//                     this._showDecreaseQuantityPopup();
//                 }
//             } else {
//                 const { buffer } = event.detail;
//                 const val = buffer === null ? 'remove' : buffer;
//                 this._setValue(val);
//             }

//             // Always clean up temp_uom_id after using
//             delete selectedLine.product.temp_uom_id;
//         }

//     };
//     Registries.Component.extend(ProductScreen, PosFrProductScreen);
//     return ProductScreen;
// });