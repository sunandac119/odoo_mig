odoo.define('stock_barcode_parent_template_validate.barcode_qr_scanner', function(require) {
    "use strict";

    const AbstractField = require('web.AbstractField');
    const fieldRegistry = require('web.field_registry');

    const BarcodeScanner = AbstractField.extend({
        template: 'barcode_qr_scanner_template',
        events: {
            'click .scan-btn': '_onScanClick',
        },

        _onScanClick: function () {
            const self = this;
            navigator.mediaDevices.getUserMedia({ video: { facingMode: "environment" } }).then(function(stream) {
                const video = document.createElement('video');
                video.srcObject = stream;
                video.setAttribute("playsinline", true);
                video.play();
                requestAnimationFrame(tick);
                function tick() {
                    if (video.readyState === video.HAVE_ENOUGH_DATA) {
                        const canvas = document.createElement("canvas");
                        canvas.width = video.videoWidth;
                        canvas.height = video.videoHeight;
                        const ctx = canvas.getContext("2d");
                        ctx.drawImage(video, 0, 0, canvas.width, canvas.height);
                        const imageData = ctx.getImageData(0, 0, canvas.width, canvas.height);
                        const code = jsQR(imageData.data, imageData.width, imageData.height, {
                            inversionAttempts: "dontInvert",
                        });
                        if (code) {
                            stream.getTracks().forEach(track => track.stop());
                            self._setValue(code.data);
                            return;
                        }
                    }
                    requestAnimationFrame(tick);
                }
            });
        },
    });

    fieldRegistry.add('barcode_qr_scanner', BarcodeScanner);
});