odoo.define('stock_inventory_html5_qrcode_scan.html5_barcode_scanner', function (require) {
    "use strict";

    const FormController = require('web.FormController');
    const FormView = require('web.FormView');
    const viewRegistry = require('web.view_registry');

    const HTML5ScanFormController = FormController.extend({
        events: Object.assign({}, FormController.prototype.events, {
            'click .o_mobile_scan_button': '_onScanClick',
        }),

        _onScanClick: function () {
            const self = this;
            const readerDiv = document.getElementById("reader");
            readerDiv.style.display = "block";

            const html5QrCode = new Html5Qrcode("reader");
            html5QrCode.start(
                { facingMode: "environment" },
                { fps: 10, qrbox: 250 },
                (decodedText, decodedResult) => {
                    html5QrCode.stop().then(() => {
                        readerDiv.style.display = "none";
                        self._rpc({
                            model: 'product.product',
                            method: 'search_read',
                            args: [[['barcode', '=', decodedText]], ['id', 'display_name', 'uom_id']],
                            limit: 1,
                        }).then(products => {
                            if (products.length) {
                                const product = products[0];
                                self.changes.product_id = product.id;
                                self.changes.product_uom_id = product.uom_id && product.uom_id[0];
                                self.render();
                            } else {
                                alert("No product found for barcode: " + decodedText);
                            }
                        });
                    }).catch(err => {
                        console.error("Failed to stop html5QrCode", err);
                    });
                },
                (errorMessage) => {
                    // optionally show scan error
                }
            );
        },
    });

    const HTML5ScanFormView = FormView.extend({
        config: Object.assign({}, FormView.prototype.config, {
            Controller: HTML5ScanFormController,
        }),
    });

    viewRegistry.add('form_with_html5_qrcode_scan', HTML5ScanFormView);
});
