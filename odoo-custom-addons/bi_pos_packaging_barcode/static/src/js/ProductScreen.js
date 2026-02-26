odoo.define('bi_pos_packaging_barcode.ProductScreen', function(require) {
	"use strict";
	const { useRef } = owl.hooks;
    const { debounce } = owl.utils;
    const { posbus } = require('point_of_sale.utils');
	const Registries = require('point_of_sale.Registries');
	const ProductScreen = require('point_of_sale.ProductScreen');

	const BiProductScreen = (ProductScreen) =>
		class extends ProductScreen {
			constructor() {
				super(...arguments);
			}
			async _getAddProductOptions(product, base_code) {
	            let price_extra = 0.0;
	            let draftPackLotLines, weight, description, packLotLinesToEdit;

	            if (this.env.pos.config.product_configurator && _.some(product.attribute_line_ids, (id) => id in this.env.pos.attributes_by_ptal_id)) {
	                let attributes = _.map(product.attribute_line_ids, (id) => this.env.pos.attributes_by_ptal_id[id])
	                                  .filter((attr) => attr !== undefined);
	                let { confirmed, payload } = await this.showPopup('ProductConfiguratorPopup', {
	                    product: product,
	                    attributes: attributes,
	                });

	                if (confirmed) {
	                    description = payload.selected_attributes.join(', ');
	                    price_extra += payload.price_extra;
	                } else {
	                    return;
	                }
	            }

	            // Gather lot information if required.
	            if (['serial', 'lot'].includes(product.tracking) && (this.env.pos.picking_type.use_create_lots || this.env.pos.picking_type.use_existing_lots)) {
	                const isAllowOnlyOneLot = product.isAllowOnlyOneLot();
	                if (isAllowOnlyOneLot) {
	                    packLotLinesToEdit = [];
	                } else {
	                    const orderline = this.currentOrder
	                        .get_orderlines()
	                        .filter(line => !line.get_discount())
	                        .find(line => line.product.id === product.id);
	                    if (orderline) {
	                        packLotLinesToEdit = orderline.getPackLotLinesToEdit();
	                    } else {
	                        packLotLinesToEdit = [];
	                    }
	                }
	                const { confirmed, payload } = await this.showPopup('EditListPopup', {
	                    title: this.env._t('Lot/Serial Number(s) Required'),
	                    isSingleItem: isAllowOnlyOneLot,
	                    array: packLotLinesToEdit,
	                });
	                if (confirmed) {
	                    // Segregate the old and new packlot lines
	                    const modifiedPackLotLines = Object.fromEntries(
	                        payload.newArray.filter(item => item.id).map(item => [item.id, item.text])
	                    );
	                    const newPackLotLines = payload.newArray
	                        .filter(item => !item.id)
	                        .map(item => ({ lot_name: item.text }));

	                    draftPackLotLines = { modifiedPackLotLines, newPackLotLines };
	                } else {
	                    // We don't proceed on adding product.
	                    return;
	                }
	            }

	            // Take the weight if necessary.
	            if (product.to_weight && this.env.pos.config.iface_electronic_scale) {
	                // Show the ScaleScreen to weigh the product.
	                if (this.isScaleAvailable) {
	                    const { confirmed, payload } = await this.showTempScreen('ScaleScreen', {
	                        product,
	                    });
	                    if (confirmed) {
	                        weight = payload.weight;
	                    } else {
	                        // do not add the product;
	                        return;
	                    }
	                } else {
	                    await this._onScaleNotAvailable();
	                }
	            }
		        if (base_code && this.env.pos.db.product_packaging_by_barcode[base_code.code]) {
	                weight = this.env.pos.db.product_packaging_by_barcode[base_code.code].qty;
	            }

	            return { draftPackLotLines, quantity: weight, description, price_extra };
        	}
        	async _barcodeProductAction(code) {
	            const product = this.env.pos.db.get_product_by_barcode(code.base_code)
	            if (!product) {
	                // find the barcode in the backend
	                let foundProductIds = [];
	                try {
	                    foundProductIds = await this.rpc({
	                        model: 'product.product',
	                        method: 'search',
	                        args: [[['barcode', '=', code.base_code]]],
	                        context: this.env.session.user_context,
	                    });
	                } catch (error) {
	                    if (isConnectionError(error)) {
	                        return this.showPopup('OfflineErrorPopup', {
	                            title: this.env._t('Network Error'),
	                            body: this.env._t("Product is not loaded. Tried loading the product from the server but there is a network error."),
	                        });
	                    } else {
	                        throw error;
	                    }
	                }
	                if (foundProductIds.length) {
	                    await this.env.pos._addProducts(foundProductIds);
	                    // assume that the result is unique.
	                    product = this.env.pos.db.get_product_by_id(foundProductIds[0]);
	                } else {
	                    return this._barcodeErrorAction(code);
	                }
	            }
            	const options = await this._getAddProductOptions(product, code);
	            // Do not proceed on adding the product when no options is returned.
	            // This is consistent with _clickProduct.
	            if (!options) return;

	            // update the options depending on the type of the scanned code
	            if (code.type === 'price') {
	                Object.assign(options, {
	                    price: code.value,
	                    extras: {
	                        price_manually_set: true,
	                    },
	                });
	            } else if (code.type === 'weight') {
	                Object.assign(options, {
	                    quantity: code.value,
	                    merge: false,
	                });
	            } else if (code.type === 'discount') {
	                Object.assign(options, {
	                    discount: code.value,
	                    merge: false,
	                });
	            }
	            this.currentOrder.add_product(product,  options)
	        }
		};

	Registries.Component.extend(ProductScreen, BiProductScreen);

	return ProductScreen;

});
