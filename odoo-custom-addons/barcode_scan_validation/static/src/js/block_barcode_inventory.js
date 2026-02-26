odoo.define('block_scan_parent_template.LinesWidgetPatch', function (require) {
    'use strict';

    var core = require('web.core');
    const LinesWidget = require('stock_barcode.LinesWidget');
    const rpc = require('web.rpc');
    const _t = core._t;

    const originalAddProduct = LinesWidget.prototype.addProduct;

    LinesWidget.include({
        init: function (parent, page, pageIndex, nbPages) {
            this._super.apply(this, arguments);
        },

        async addProduct(lineDescription, model, doNotClearLineHighlight) {
            let productList = [];

            for (let i = 0; i < this?.page?.lines?.length; i++) {
                let line = this.page.lines[i];
                if (line?.product_id?.id) {
                    productList.push(line.product_id.id);
                }
            }

            const productData = await rpc.query({
                model: 'product.product',
                method: 'read',
                args: [productList, ['product_tmpl_id', 'parent_template_id']],
            });

            for (let i = 0; i < productData.length; i++) {
                const tmplId = productData[i].product_tmpl_id?.[0]; // ID only
                const parentTmplId = productData[i].parent_template_id?.[0]; // ID only

                console.log("tmplId:", tmplId, "parentTmplId:", parentTmplId);

                if (tmplId && parentTmplId && tmplId !== parentTmplId) {
                    this.do_notify(
                        _t("Template Mismatch"),
                        _t("The scanned product does not match the parent template ID.")
                    );
                    return;
                }
            }

            // Call original addProduct method to keep UI and logic intact
            return originalAddProduct.apply(this, arguments);
        },
    });
});
