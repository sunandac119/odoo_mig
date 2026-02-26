odoo.define('pos_multi_uom_barcode.DBPricePatch', function(require) {
    'use strict';
    const PosDB = require('point_of_sale.DB');

    PosDB.include({
        get_price_with_uom: function(product, uom_id, pricelist) {
            const items = pricelist.items || [];
            const tmpl_id = product.product_tmpl_id;

            let matched = items.find(item =>
                ((item.product_id && item.product_id[0] === product.id) ||
                 (item.product_tmpl_id && item.product_tmpl_id[0] === tmpl_id)) &&
                item.uom_id && item.uom_id[0] === uom_id
            );

            if (matched && matched.fixed_price !== undefined) {
                console.log("[UOM PRICE FOUND]", matched);
                return matched.fixed_price;
            }

            console.warn("[FALLBACK] No exact UOM match for:", tmpl_id, "UOM:", uom_id);
            const uom_ratio = this.uom_ratio_by_id && this.uom_ratio_by_id[uom_id];
            const base_price = product.lst_price || product.price || 0;
            return uom_ratio ? base_price * uom_ratio : base_price;
        }
    });

    return PosDB;
});
