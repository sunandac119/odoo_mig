odoo.define('stock_inventory_mobile_scan_button.inventory_barcode_scanner', function (require) {
    "use strict";

    const FormController = require('web.FormController');
    const FormView = require('web.FormView');
    const viewRegistry = require('web.view_registry');

    const ScanButtonFormController = FormController.extend({
        events: Object.assign({}, FormController.prototype.events, {
            'click .o_mobile_scan_button': '_onScanClick',
        }),

        _onScanClick: function () {
            if (!navigator.mediaDevices || !navigator.mediaDevices.getUserMedia) {
                alert("This device or browser doesn't support camera scanning.");
                return;
            }

            const input = document.createElement('input');
            input.type = 'file';
            input.accept = 'image/*';
            input.capture = 'environment';
            input.click();

            input.onchange = function () {
                const file = input.files[0];
                const reader = new FileReader();

                reader.onload = function () {
                    alert("Image captured. Implement decoding or backend send.");
                };

                reader.readAsDataURL(file);
            };
        },
    });

    const ScanButtonFormView = FormView.extend({
        config: Object.assign({}, FormView.prototype.config, {
            Controller: ScanButtonFormController,
        }),
    });

    viewRegistry.add('form_with_inventory_scan', ScanButtonFormView);
});
