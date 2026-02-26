odoo.define('add_product_sale_order.ProductKanbanRenderer', function (require) {
"use strict";

const KanbanRenderer = require('web.KanbanRenderer');
const KanbanRecord = require('add_product_sale_order.ProductKanbanRecord');

return KanbanRenderer.extend({
    config: _.extend({}, KanbanRenderer.prototype.config, {
        KanbanRecord
    }),
});

});
