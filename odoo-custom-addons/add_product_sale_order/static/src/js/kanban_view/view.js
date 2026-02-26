odoo.define('add_product_sale_order.ProductKanbanView', function (require) {
"use strict";

const KanbanView = require('web.KanbanView');
const KanbanModel = require('add_product_sale_order.ProductKanbanModel');
const KanbanController = require('add_product_sale_order.ProductKanbanController');
const KanbanRenderer = require('add_product_sale_order.ProductKanbanRenderer');
const viewRegistry = require('web.view_registry');

const ProductKanbanView = KanbanView.extend({
    config: _.extend({}, KanbanView.prototype.config, {
        Model: KanbanModel,
        Controller: KanbanController,
        Renderer: KanbanRenderer,
    }),
});

viewRegistry.add('fsm_product_kanban', ProductKanbanView);

return ProductKanbanView;

});
