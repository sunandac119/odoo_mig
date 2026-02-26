odoo.define('pos_search_products_by_numbers.ProductsWidgetControlPanel', function(require) {
    'use strict';

    const { useRef } = owl.hooks;
    const { debounce } = owl.utils;
    const { identifyError } = require('point_of_sale.utils');
    const PosProductsWidgetControlPanelComponent = require('point_of_sale.ProductsWidgetControlPanel');
    const Registries = require('point_of_sale.Registries');
    const { posbus } = require('point_of_sale.utils');

    class ProductsWidgetControlPanel extends PosProductsWidgetControlPanelComponent {
        constructor() {
            super(...arguments);
            this.SearchByNumbersOnly = debounce(this.SearchByNumbersOnly, 1);
        }
        SearchByNumbersOnly(event){
            var NumbersRegex = event.target.value.replace(new RegExp(/[^\d]/,'ig'), "");
            event.target.value = NumbersRegex;
        }
    }
    ProductsWidgetControlPanel.template = 'ProductsWidgetControlPanel';
    Registries.Component.add(ProductsWidgetControlPanel);
    return ProductsWidgetControlPanel;
});
