odoo.define('bi_pos_closed_session_reports.SessionReport', function(require) {
    'use strict';

    const PosComponent = require('point_of_sale.PosComponent');
    const ProductScreen = require('point_of_sale.ProductScreen');
    const Registries = require('point_of_sale.Registries');
    const { useListener } = require('web.custom_hooks');
    const { useState, useRef } = owl.hooks;

    class SessionReport extends PosComponent {
        constructor() {
            super(...arguments);
           useListener('click', this._onClick);
        }
        async _onClick() {
            var self = this;
            var pos_session_id = self.env.pos.pos_session.id;
                await this.env.pos.do_action('bi_pos_closed_session_reports.action_report_session_z', {
                    additional_context: {
                        active_ids: [self.env.pos.pos_session.id],
                    },
                });
        }
    }
    SessionReport.template = 'SessionReport';

    ProductScreen.addControlButton({
        component: SessionReport,
        condition: function() {
            return this.env.pos.config.enable_session_report;
        },
    });

    Registries.Component.add(SessionReport);

    return SessionReport;
});
