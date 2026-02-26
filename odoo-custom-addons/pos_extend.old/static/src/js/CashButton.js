odoo.define('pos_extend.CashButton', function (require) {
    "use strict";

    const CashBoxOpening = require('point_of_sale.CashBoxOpening');
    const Registries = require('point_of_sale.Registries');

    const PosCashBoxOpening = CashBoxOpening => class extends CashBoxOpening {
        constructor() {
            super(...arguments);
        }

        async onClick() {
            // Print "open drawer" to the printer
            await this.printTextToPrinter('open drawer');

            var self = this;
            const { confirmed, payload } = await this.showPopup('CashBoxPopup', {
                title: this.env._t('Cash Control'),
                body: this.env._t('This click is successfully done.'),
                printText: 'PRINT',
                confirmText: 'CONFIRM',
                cancelText: 'CANCEL',
            });

            if (confirmed) {
                var value = $('.cashbox-input').val();
                this.changes['cashBoxValue'] = value;
            }
        }

        async printTextToPrinter(text) {
            return new Promise((resolve, reject) => {
                if (window.print) {
                    const printWindow = window.open('', '_blank');
                    
                    // Set the paper size to 70mm width and 20mm height
                    printWindow.document.write(`
                        <html>
                            <head>
                                <style>
                                    @media print {
                                        @page {
                                            size: 80mm 210mm; 
                                            margin: 0;
                                        }
                                        body {
                                            margin: 0;
                                            font-family: Arial, sans-serif; /* Adjust font-family if needed */
                                        }
                                    }
                                </style>
                            </head>
                            <body>${text}</body>
                        </html>
                    `);

                    printWindow.document.close();
                    printWindow.focus();
                    printWindow.print();

                    // Wait for a brief delay before closing the window
                    setTimeout(() => {
                        printWindow.close();
                        resolve();
                    }, 10); // Adjust the delay as needed
                } else {
                    reject(new Error('Printing is not supported in this browser.'));
                }
            });
        }
    };

    Registries.Component.extend(CashBoxOpening, PosCashBoxOpening);

    return CashBoxOpening;
});
