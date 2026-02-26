odoo.define('product_return_pos.order_list_screen', function(require) {
    "use strict";

    const { useListener } = require('web.custom_hooks');
    const PosComponent = require('point_of_sale.PosComponent');
    const Registries = require('point_of_sale.Registries');
    const { Order } = require('point_of_sale.models');
    const { Gui } = require('point_of_sale.Gui');

    class OrderListScreenWidget extends PosComponent {
        constructor() {
            super(...arguments);
            useListener('filter-selected', this._onFilterSelected);
            useListener('search', this._onSearch);
            this.searchDetails = {};
            this.filter = null;
            this._initializeSearchFieldConstants();
        }

        mounted() {
            this.render();
        }

        back() {
            this.close();
        }

        reload() {
            window.location.reload();
        }

        return_click(order) {
            this.create_return_order(order, order.partner_id && order.partner_id[0]);
        }

        create_return_order(order, client_id) {
            const pos = this.env.pos;
            const returnOrder = new Order({}, { pos });

            if (client_id) {
                const client = pos.db.get_partner_by_id(client_id);
                if (client) returnOrder.set_client(client);
            }

            if (order && order.lines) {
                order.lines.forEach((line) => {
                    returnOrder.add_product(pos.db.get_product_by_id(line.product_id[0]), {
                        quantity: -Math.abs(line.qty),
                        price: line.price_unit,
                        discount: line.discount,
                    });
                });
            }

            if (pos.get_order()) {
                pos.get_order().destroy();
            }
            pos.get('orders').add(returnOrder);
            pos.set_order(returnOrder);

            this.showScreen('PaymentScreen');
        }

        get ordersList() {
            const { fieldValue, searchTerm } = this.searchDetails;
            const fieldAccessor = this._searchFields[fieldValue];
            return this.orderList.filter(order => {
                if (!fieldAccessor) return true;
                const fieldValue = fieldAccessor(order);
                if (fieldValue === null || !searchTerm) return true;
                return fieldValue.toString().toLowerCase().includes(searchTerm.toLowerCase());
            });
        }

        _onFilterSelected(event) {
            this.filter = event.detail.filter;
            this.render();
        }

        get orderList() {
            return this.env.pos.orders || [];
        }

        get _searchFields() {
            return {
                'Receipt Number': (order) => order.name,
                Date: (order) => order.date_order,
                Customer: (order) => order.partner_id[1],
                'Return Ref': (order) => order.return_ref,
            };
        }

        _onSearch(event) {
            Object.assign(this.searchDetails, event.detail);
            this.render();
        }

        get searchBarConfig() {
            return {
                searchFields: this.constants.searchFieldNames,
                filter: { show: true, options: this.filterOptions },
            };
        }

        get filterOptions() {
            return ['All Orders'];
        }

        get _screenToStatusMap() {
            return {
                ProductScreen: 'Ongoing',
                PaymentScreen: 'Payment',
                ReceiptScreen: 'Receipt',
            };
        }

        _initializeSearchFieldConstants() {
            this.constants = {
                searchFieldNames: Object.keys(this._searchFields),
                screenToStatusMap: this._screenToStatusMap,
            };
        }
    }

    OrderListScreenWidget.template = 'OrderListScreenWidget';
    Registries.Component.add(OrderListScreenWidget);

    return OrderListScreenWidget;
});