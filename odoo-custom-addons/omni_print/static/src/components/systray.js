odoo.define('omni_print.PrintTrayMenu', function (require) {
    "use strict";

    var SystrayMenu = require('web.SystrayMenu');
    var Widget = require('web.Widget');
    var heartbeatService = require('omni_print.heartbeat_service');

    var PrintTrayMenu = Widget.extend({
        template: 'omni_print.PrintTrayMenu',
        events: {
            'click': '_onClick',
        },

        init: function () {
            this._super.apply(this, arguments);
            this.state = {
                connection: "unknown",
            };
            this.heartbeatService = null;
        },

        start: async function () {
            var self = this;
            await this._super.apply(this, arguments);
            self.heartbeatService = await heartbeatService;
            self._registerHeartbeatHooks(self.heartbeatService);
            self.$el.on('click', self._onClickDropdown.bind(self));
        },

        _registerHeartbeatHooks: function (heartbeatService) {
            var self = this;
            heartbeatService.bus.on("onopen", function () {
                self.state.connection = "online";
                self._updateDisplay();
            });
            heartbeatService.bus.on("onmessage", function () {
                self.state.connection = "online";
                self._updateDisplay();
            });
            heartbeatService.bus.on("onerror", function () {
                self.state.connection = "unknown";
                self._updateDisplay();
            });
            heartbeatService.bus.on("onclose", function () {
                self.state.connection = "offline";
                self._updateDisplay();
            });

            if (heartbeatService.isAlive()) {
                self.state.connection = "online";
                self._updateDisplay();
            }
        },

        _onClick: function () {
            if (this.state.connection !== "online") {
                this.heartbeatService.setupConnection();
            }
        },

        _onClickDropdown: function (event) {
            event.preventDefault();
            this.$el.toggleClass('show');
        },

        _updateDisplay: function () {
            this.renderElement();
            this.$('.dropdown-menu').toggleClass('show', this.$el.hasClass('show'));
        },

        destroy: function () {
            if (this.heartbeatService) {
                this.heartbeatService.closeConnection();
            }
            this._super.apply(this, arguments);
        },
    });

    SystrayMenu.Items.push(PrintTrayMenu);

    return PrintTrayMenu;
});
