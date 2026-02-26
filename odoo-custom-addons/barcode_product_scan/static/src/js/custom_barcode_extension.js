odoo.define('your_module.LinesWidgetRestriction', function (require) {
    'use strict';

    var LinesWidget = require('stock_barcode.LinesWidget');
    var core = require('web.core');
    var _t = core._t;

    LinesWidget.include({

        init: function (parent, page, pageIndex, nbPages) {
            this._super.apply(this, arguments);

            this.allowedProducts = [];
            if (this.page && this.page.lines && this.page.lines.length > 0) {
                this.allowedProducts = this.page.lines
                    .filter(function(line) { return line.product_id; })
                    .map(function(line) {
                        let res = {
                            id: line.product_id.id,
                            barcode: line.product_barcode || line.product_id.barcode,
                            qty: line.product_uom_qty
                        };
                        return res
                    });
            }
        },

// #####################################################################################################################
        // addProduct: function (lineDescription, model, doNotClearLineHighlight) {

        //     if (!lineDescription.product_id && !lineDescription.product_barcode) {
        //         return false;
        //     }

        //     if (this.allowedProducts && this.allowedProducts.length) {

        //         const isAllowed = this.allowedProducts.some(p =>
        //             (lineDescription.product_id && p.id === lineDescription.product_id.id) ||
        //             (lineDescription.product_barcode && p.barcode === lineDescription.product_barcode)
        //         );

        //         if (!isAllowed) {
        //             this.displayNotification({
        //                 title: _t('Not Allowed'),
        //                 message: _t('You are not allowed to scan this product.'),
        //                 type: 'danger',
        //             });
        //             return false;
        //         }
        //     }


        //     const result = this._super.apply(this, arguments);


        //     const scannedLine = this.page.lines.find(l =>
        //         (lineDescription.product_id && l.product_id.id === lineDescription.product_id.id) ||
        //         (lineDescription.product_barcode && l.product_barcode === lineDescription.product_barcode)
        //     );

        //     if (!scannedLine) return result;

        //     const qtyDone = scannedLine.qty_done || 0;
        //     const demandQty = scannedLine.product_uom_qty || 0;

        //     if (qtyDone > demandQty) {
        //         // rollback last increment
        //         scannedLine.qty_done = demandQty;

        //         this.displayNotification({
        //             title: _t('Qty Exceeded'),
        //             message: _t('You have already scanned the maximum quantity for this product.'),
        //             type: 'warning',
        //         });

        //         this.trigger('reload');
        //         return false;
        //     }

        //     return result;
        // }

// #####################################################################################################################

// #####################################################################################################################
        addProduct: function (lineDescription, model, doNotClearLineHighlight) {

            if (!lineDescription.product_id && !lineDescription.product_barcode) {
                return false;
            }


            // If no allowedProducts defined (no PO linked), allow all scans
            if (!this.allowedProducts || this.allowedProducts.length === 0) {
                return this._super.apply(this, arguments);
            }

            var allowedLine = this.allowedProducts.find(function (p) {
                var match =
                    (lineDescription.product_id && p.id === lineDescription.product_id.id) ||
                    (lineDescription.product_barcode && p.barcode === lineDescription.product_barcode);

                if (match) {
                }
                return match;
            });

            if (!allowedLine) {

                this.displayNotification({
                    title: _t('Not Allowed'),
                    message: _t('You are not allowed to scan this product.'),
                    type: 'danger',
                });
                return false;
            }

            // Check scanned qty
            var existingLine = this.page.lines.find(function (l) {
                return l.product_id && l.product_id.id === allowedLine.id;
            });


            if (existingLine) {
                console.log(
                    "Qty done:",
                    existingLine.qty_done,
                    "Allowed qty:",
                    allowedLine.qty
                );
            }

            if (existingLine && existingLine.qty_done >= allowedLine.qty) {
                console.warn("Quantity exceeded for product:", allowedLine);

                this.displayNotification({
                    title: _t('Qty Exceeded'),
                    message: _t('You have already scanned the maximum quantity for this product.'),
                    type: 'warning',
                });
                return false;
            }

            return this._super.apply(this, arguments);
        },


        // ###############################################################################

        _updateIncrementButtons: function ($line) {
            if (!$line || !$line.length) return;
            const id = $line.data('id');
            const line = this.page.lines.find(l => id === (l.id || l.virtual_id));
            if (!line) return;

            const qtyDone = parseFloat($line.find('.qty-done').text() || 0);

            if (this.model === 'stock.inventory') {
                const hideAddButton = Boolean(
                    (line.product_id.tracking === 'serial' && (!line.prod_lot_id || line.product_qty > 0)) ||
                    (line.product_id.tracking === 'lot' && !line.prod_lot_id)
                );
                const hideRemoveButton = (line.product_qty < 1);
                $line.find('.o_add_unit').toggleClass('d-none', hideAddButton);
                $line.find('.o_remove_unit').toggleClass('d-none', hideRemoveButton);
            } else {
                if (line.product_uom_qty === 0) return;
                if (qtyDone < line.product_uom_qty) {
                    const $button = $line.find('button[class*="o_add_"]');
                    const remainingQty = line.product_uom_qty - qtyDone;

                    if (this.istouchSupported) {
                        const $reservedButton = $button.filter('.o_add_reserved');
                        $button.data('reserved', remainingQty);
                        $reservedButton.text(`+ ${remainingQty}`);
                    } else if (this.shiftPressed) {
                        $button.data('reserved', remainingQty);
                        $button.text(`+ ${remainingQty}`);
                        $button.toggleClass('o_add_reserved', true);
                        $button.toggleClass('o_add_unit', false);
                    } else {
                        $button.text('+ 1');
                        $button.toggleClass('o_add_unit', true);
                        $button.toggleClass('o_add_reserved', false);
                    }
                } else {
                    $line.find('.o_line_button').hide();
                    $line.addClass('o_line_qty_completed');
                    if (!(line.product_id.tracking === 'serial' || line.product_id.tracking === 'lot') || line.lot_name) {
                        $line.parent().append($line);
                        $line.addClass('o_line_completed');
                    }
                }
            }
        },

        _scrollToLine: function ($body, $line) {
            if (!$line || !$line.length) return;
            this._super.apply(this, arguments);
        },
    });
});

        // addProduct: function (lineDescription, model, doNotClearLineHighlight) {
        //     console.log('[CUSTOM] addProduct called');
        //     console.log('[CUSTOM] lineDescription:', lineDescription);

        //     if (!lineDescription.product_id && !lineDescription.product_barcode) {
        //         console.log('[CUSTOM] No product info, stopping');
        //         return false;
        //     }

        //     if (!this.allowedProducts || !this.allowedProducts.length) {
        //         console.log('[CUSTOM] No restriction, calling super');
        //         return this._super.apply(this, arguments);
        //     }

        //     var allowedLine = this.allowedProducts.find(function (p) {
        //         return (
        //             (lineDescription.product_id && p.id === lineDescription.product_id.id) ||
        //             (lineDescription.product_barcode && p.barcode === lineDescription.product_barcode)
        //         );
        //     });

        //     if (!allowedLine) {
        //         console.log('[CUSTOM] Product NOT allowed, removing temporary line');

        //         // REMOVE temporary line from page.lines (CRITICAL FIX)
        //         if (this.page && this.page.lines) {
        //             this.page.lines = this.page.lines.filter(function (l) {
        //                 return l.virtual_id !== lineDescription.virtual_id;
        //             });
        //         }

        //         this.displayNotification({
        //             title: _t('Not Allowed'),
        //             message: _t('This product is not part of the current picking.'),
        //             type: 'danger',
        //         });

        //         return false;
        //     }

        //     console.log('[CUSTOM] Product allowed, calling super');
        //     return this._super.apply(this, arguments);
        // },

        // ################################################################################
        // addProduct: function (lineDescription, model, doNotClearLineHighlight) {
        //     console.log("addProduct (BASE) completed");
        //     if (!lineDescription.product_id && !lineDescription.product_barcode) {
        //         // return;
        //         return false;
        //     }

        //     // If no allowedProducts defined (no PO linked), allow all scans
        //     if (!this.allowedProducts || this.allowedProducts.length === 0) {
        //         return this._super.apply(this, arguments);
        //     }

        //     var allowedLine = this.allowedProducts.find(function(p) {
        //         return (lineDescription.product_id && p.id === lineDescription.product_id.id) ||
        //                (lineDescription.product_barcode && p.barcode === lineDescription.product_barcode);
        //     });

        //     if (!allowedLine) {
        //         this.displayNotification({
        //             title: _t('Not Allowed'),
        //             message: _t('You are not allowed to scan this product.'),
        //             type: 'danger',
        //         });
        //         // return;
        //         return false;
        //     }

        //     // Check scanned qty
        //     var existingLine = this.page.lines.find(function(l) {
        //         return l.product_id && l.product_id.id === allowedLine.id;
        //     });
        //     if (existingLine && existingLine.qty_done >= allowedLine.qty) {
        //         this.displayNotification({
        //             title: _t('Qty Exceeded'),
        //             message: _t('You have already scanned the maximum quantity for this product.'),
        //             type: 'warning',
        //         });
        //         // return;
        //         return false;
        //     }

        //     return this._super.apply(this, arguments);
        // },