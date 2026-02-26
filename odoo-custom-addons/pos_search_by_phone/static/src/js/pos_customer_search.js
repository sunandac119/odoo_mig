odoo.define('pos_custom.search_by_phone', function(require) {
    "use strict";

    var models = require('point_of_sale.models');

    // Extend the Partner model to include phone number in search fields
    models.load_fields('res.partner', ['phone', 'mobile']);

    var _super_partner = models.PosDB.prototype.search_partner;
    models.PosDB.prototype.search_partner = function(query) {
        var results = _super_partner.apply(this, arguments);
        if (!query) {
            return results;
        }

        var query_lower = query.toLowerCase();
        return results.filter(function(partner) {
            return (partner.phone && partner.phone.toLowerCase().includes(query_lower)) ||
                   (partner.mobile && partner.mobile.toLowerCase().includes(query_lower)) ||
                   partner.name.toLowerCase().includes(query_lower) ||
                   partner.email && partner.email.toLowerCase().includes(query_lower);
        });
    };
});
