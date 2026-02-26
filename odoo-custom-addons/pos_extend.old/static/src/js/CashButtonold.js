odoo.define('pos_extend.CashButton', function (require) {
    'use strict';

    const PosComponent = require('point_of_sale.PosComponent');
    const Registries = require('point_of_sale.Registries');
    const { posbus } = require('point_of_sale.utils');


    class CashButton extends PosComponent {
        async onClick() {
            var self = this;
            const { confirmed, payload } = await this.showPopup('CashBoxPopup', {
                title: this.env._t('Cash Control'),
                body: this.env._t('This click is successfully done.'),
                confirmText: 'CONFIRM',
                cancelText: 'CANCEL',
            });
            if (confirmed) {

                // console.log(self.changes, 'this.changes')
                // self.defaultValue = payload.cashOpeningTotal
                // self.env.pos.bank_statement.balance_start = total.toFixed(2)

                // this.changes['cashBoxValue'] = payload.cashOpeningTotal;


                console.log(payload.cashOpeningTotal, 'payload')
                console.log(payload, 'payload')
            }
        }
    }
    CashButton.template = 'CashButton';

    Registries.Component.add(CashButton);

    return CashButton;
});
