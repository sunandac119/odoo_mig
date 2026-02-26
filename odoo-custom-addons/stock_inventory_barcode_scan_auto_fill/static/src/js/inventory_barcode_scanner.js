odoo.define('stock_inventory_barcode_scan_auto_fill.inventory_barcode_scanner', function (require) {
    "use strict";

    const FormController = require('web.FormController');
    const FormView = require('web.FormView');
    const viewRegistry = require('web.view_registry');

    const ScanFormController = FormController.extend({
        events: Object.assign({}, FormController.prototype.events, {
            'click .o_mobile_scan_button': '_onScanClick',
        }),

        _onScanClick: function () {
            const input = document.createElement('input');
            input.type = 'file';
            input.accept = 'image/*';
            input.capture = 'environment';
            input.click();

            input.onchange = () => {
                const file = input.files[0];
                const reader = new FileReader();
                reader.onload = () => {
                    const base64 = reader.result;

                    // Simulated scanned barcode for demo
                    const scannedBarcode = prompt("Simulated Scan: Enter barcode manually", "1234567890123");
                    if (scannedBarcode) {
                        this._rpc({
                            model: 'product.product',
                            method: 'search_read',
                            args: [[['barcode', '=', scannedBarcode]], ['id', 'display_name', 'uom_id']],
                            limit: 1,
                        }).then(products => {
                            if (products.length) {
                                const product = products[0];
                                this.changes.product_id = product.id;
                                this.changes.product_uom_id = product.uom_id && product.uom_id[0];
                                this.render();
                            } else {
                                alert("No product found for barcode: " + scannedBarcode);
                            }
                        });
                    }
                };
                reader.readAsDataURL(file);
            };
        },
    });

    const ScanFormView = FormView.extend({
        config: Object.assign({}, FormView.prototype.config, {
            Controller: ScanFormController,
        }),
    });

    viewRegistry.add('form_with_barcode_scan_autofill', ScanFormView);
});
