odoo.define('pos_restrict_disc_amt.models', function(require) {
    "use strict";

    const models = require('point_of_sale.models');
    models.load_fields('res.users', ['allow_pos_discount', 'allow_pos_price']);
});
