odoo.define('uom_barcode_scanner.EnterFocusQty', function (require) {
    "use strict";

    var ListRenderer = require('web.ListRenderer');
    var FieldOne2Many = require('web.relational_fields').FieldOne2Many;
    var fieldRegistry = require('web.field_registry');

    var EnterQtyListRenderer = ListRenderer.extend({
        // Bind once at the renderer level; survives row re-renders
        events: _.extend({}, ListRenderer.prototype.events, {
            'keydown td.o_data_cell': '_onCellKeydown',
        }),

        _onCellKeydown: function (ev) {
            console.log('evvvv',ev)
            console.log('evvvv.key',ev.key)
            if (ev.key !== 'Enter') return;

            // kill Odoo's default Enter handling (which creates/moves to a new line)
            ev.preventDefault();
            ev.stopPropagation();
            ev.stopImmediatePropagation();

            var $td  = $(ev.currentTarget);
            var $row = $td.closest('tr');

            // pick either picking qty or sale order qty
            var $qtyCell = $row.find('td.o_data_cell[data-name="qty_done"], td.o_data_cell[data-name="product_uom_qty"]');
            if (!$qtyCell.length) return;

            // force editable mode on the qty cell
            $qtyCell.trigger('click');

            // wait for Odoo to swap <span> → <input>
            setTimeout(function () {
                var input = $qtyCell.find('input')[0];
                if (input) {
                    // empty + focus (change to just focus if you don't want clearing)
                    input.value = '';
                    input.focus();
                    input.select();
                }
            }, 0);
        },
    });

    var EnterQtyOne2Many = FieldOne2Many.extend({
        _getRenderer: function () {
            if (this.view.arch.tag === 'tree') {
                return EnterQtyListRenderer;
            }
            return this._super.apply(this, arguments);
        },
    });

    // Safer: register a custom widget and use it only where you need it
    fieldRegistry.add('one2many_enter_qty', EnterQtyOne2Many);

    return {
        EnterQtyListRenderer: EnterQtyListRenderer,
        EnterQtyOne2Many: EnterQtyOne2Many,
    };
});
