odoo.define('pos_manager_validation.pos_manager_validation', function (require) {
"use strict";

const Chrome = require('point_of_sale.Chrome');
const NumberBuffer = require('point_of_sale.NumberBuffer');
const NumpadWidget = require('point_of_sale.NumpadWidget');
const ProductScreen = require('point_of_sale.ProductScreen');
const Registries = require('point_of_sale.Registries');
const TicketScreen = require('point_of_sale.TicketScreen');

var models = require('point_of_sale.models');


models.load_fields('res.users', ['pos_security_pin'])


const PosUserValidChrome = (Chrome) =>
    class extends Chrome {
        async _closePos() {
            if (this.env.pos.config.iface_validate_close) {
                var managerUserIDs = this.env.pos.config.manager_user_ids;
                var cashier = this.env.pos.get_cashier().user_id;
                if( cashier && managerUserIDs.indexOf(cashier[0]) > -1 ){
                    return await super._closePos();
                }

                const { confirmed, payload } = await this.showPopup('NumberPopup', {
                    title: this.env._t('Manager Validation'),
                    isPassword: true,
                });
                var password = payload ? payload.toString() : ''

                if (confirmed) {
                    this.env.pos.manager = false;
                    var users = this.env.pos.users;
                    for (var i = 0; i < users.length; i++) {
                        if (managerUserIDs.indexOf(users[i].id) > -1
                                && password === (users[i].pos_security_pin || '')) {
                            this.env.pos.manager = users[i];
                        }
                    }
                    if (this.env.pos.manager) {
                        await super._closePos();
                    } else {
                        await this.showPopup('ErrorPopup', {
                            title: this.env._t('Access Denied'),
                            body: this.env._t('Incorrect password!'),
                        });
                    }
                }
            } else {
                await super._closePos();
            }
        }
    };


const PosUserValidNumpadWidget = (NumpadWidget) =>
    class extends NumpadWidget {
        changeMode(mode) {
            if ((mode === 'discount' && this.env.pos.config.iface_validate_discount)
                    || (mode === 'price' && this.env.pos.config.iface_validate_price)) {
                var managerUserIDs = this.env.pos.config.manager_user_ids;
                var cashier = this.env.pos.get_cashier().user_id;
                if( cashier && managerUserIDs.indexOf(cashier[0]) > -1 ){
                    return super.changeMode(mode);
                }

                this.showPopup('NumberPopup', {
                    title: this.env._t('Manager Validation'),
                    isPassword: true,
                }).then(({ confirmed, payload }) => {
                    var password = payload ? payload.toString() : ''

                    if (confirmed) {
                        this.env.pos.manager = false;
                        var users = this.env.pos.users;
                        for (var i = 0; i < users.length; i++) {
                            if (managerUserIDs.indexOf(users[i].id) > -1
                                    && password === (users[i].pos_security_pin || '')) {
                                this.env.pos.manager = users[i];
                            }
                        }
                        if (this.env.pos.manager) {
                            super.changeMode(mode);
                        } else {
                            this.showPopup('ErrorPopup', {
                                title: this.env._t('Access Denied'),
                                body: this.env._t('Incorrect password!'),
                            });
                        }
                    }
                });
            } else {
                super.changeMode(mode);
            }
        }
    };


const PosUserValidProductScreen = (ProductScreen) =>
    class extends ProductScreen {
        _setValue(val) {
            var newQty = NumberBuffer.get() ? parseFloat(NumberBuffer.get()) : 0;
            var orderLines = this.currentOrder.get_orderlines();
            if (orderLines !== undefined && orderLines.length > 0) {
                var currentOrderLine = this.currentOrder.get_selected_orderline();
                var currentQty = this.currentOrder.get_selected_orderline().get_quantity();
                if (currentOrderLine && this.state.numpadMode === 'quantity'
                        && ((newQty < currentQty && this.env.pos.config.iface_validate_decrease_quantity)
                            || (val === 'remove' && this.env.pos.config.iface_validate_delete_orderline))) {
                    var managerUserIDs = this.env.pos.config.manager_user_ids;
                    var cashier = this.env.pos.get_cashier().user_id;
                    if( cashier && managerUserIDs.indexOf(cashier[0]) > -1 ){
                        return super._setValue(val);
                    }

                    this.showPopup('NumberPopup', {
                        title: this.env._t('Manager Validation'),
                        isPassword: true,
                    }).then(({ confirmed, payload }) => {
                        var password = payload ? payload.toString() : ''

                        if (confirmed) {
                            this.env.pos.manager = false;
                            var users = this.env.pos.users;
                            for (var i = 0; i < users.length; i++) {
                                if (managerUserIDs.indexOf(users[i].id) > -1
                                        && password === (users[i].pos_security_pin || '')) {
                                    this.env.pos.manager = users[i];
                                }
                            }
                            if (this.env.pos.manager) {
                                super._setValue(val);
                            } else {
                                this.showPopup('ErrorPopup', {
                                    title: this.env._t('Access Denied'),
                                    body: this.env._t('Incorrect password!'),
                                });
                            }
                        }
                    });
                } else {
                    super._setValue(val);
                }
            } else {
                super._setValue(val)
            }
        }

        _onClickPay() {
            if (this.env.pos.config.iface_validate_payment) {
                var managerUserIDs = this.env.pos.config.manager_user_ids;
                var cashier = this.env.pos.get_cashier().user_id;
                if( cashier && managerUserIDs.indexOf(cashier[0]) > -1 ){
                    return super._onClickPay();
                }

                this.showPopup('NumberPopup', {
                    title: this.env._t('Manager Validation'),
                    isPassword: true,
                }).then(({ confirmed, payload }) => {
                    var password = payload ? payload.toString() : ''

                    if (confirmed) {
                        this.env.pos.manager = false;
                        var users = this.env.pos.users;
                        for (var i = 0; i < users.length; i++) {
                            if (managerUserIDs.indexOf(users[i].id) > -1
                                    && password === (users[i].pos_security_pin || '')) {
                                this.env.pos.manager = users[i];
                            }
                        }
                        if (this.env.pos.manager) {
                            super._onClickPay();
                        } else {
                            this.showPopup('ErrorPopup', {
                                title: this.env._t('Access Denied'),
                                body: this.env._t('Incorrect password!'),
                            });
                        }
                    }
                });
            } else {
                super._onClickPay();
            }
        }

    };


const PosUserValidTicketScreen = (TicketScreen) =>
    class extends TicketScreen {
        async deleteOrder(order) {
            if (this.env.pos.config.iface_validate_delete_order) {
                var managerUserIDs = this.env.pos.config.manager_user_ids;
                var cashier = this.env.pos.get_cashier().user_id;
                if( cashier && managerUserIDs.indexOf(cashier[0]) > -1 ){
                    return await super.deleteOrder(order);
                }

                const { confirmed, payload } = await this.showPopup('NumberPopup', {
                    title: this.env._t('Manager Validation'),
                    isPassword: true,
                });
                var password = payload ? payload.toString() : ''

                if (confirmed) {
                    this.env.pos.manager = false;
                    var users = this.env.pos.users;
                    for (var i = 0; i < users.length; i++) {
                        if (managerUserIDs.indexOf(users[i].id) > -1
                                && password === (users[i].pos_security_pin || '')) {
                            this.env.pos.manager = users[i];
                        }
                    }
                    if (this.env.pos.manager) {
                        await super.deleteOrder(order);
                    } else {
                        await this.showPopup('ErrorPopup', {
                            title: this.env._t('Access Denied'),
                            body: this.env._t('Incorrect password!'),
                        });
                    }
                }
            } else {
                await super.deleteOrder(order);
            }
        }
    };


Registries.Component.extend(Chrome, PosUserValidChrome);
Registries.Component.extend(NumpadWidget, PosUserValidNumpadWidget);
Registries.Component.extend(ProductScreen, PosUserValidProductScreen);
Registries.Component.extend(TicketScreen, PosUserValidTicketScreen);

});
