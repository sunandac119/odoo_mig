odoo.define('custom_barcode_parent_filter.RestrictScanToParent', function (require) {
    "use strict";

    const AbstractAction = require('stock_barcode.AbstractAction');
    const rpc = require('web.rpc');
    const core = require('web.core');
    const _t = core._t;

    AbstractAction.include({
        async _barcodeProductAction(barcode) {
            const product = await this._rpc({
                model: 'product.product',
                method: 'search_read',
                args: [[['barcode', '=', barcode]], ['id', 'product_tmpl_id']],
                limit: 1,
            });

            if (product.length === 0) {
                return this._super(...arguments);
            }

            const prod = product[0];
            const tmpl = await this._rpc({
                model: 'product.template',
                method: 'read',
                args: [[prod.product_tmpl_id[0]], ['id', 'parent_template_id']],
            });

            if (tmpl.length && tmpl[0].parent_template_id && tmpl[0].parent_template_id[0] !== tmpl[0].id) {
                this.do_warn(_t("Scan Blocked"), _t("Only parent template products are allowed."));
                return Promise.resolve(); // skip further action
            }

            return this._super(...arguments); // continue if valid
        }
    });
});
