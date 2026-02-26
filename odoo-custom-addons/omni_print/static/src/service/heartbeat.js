odoo.define('omni_print.HeartbeatConnectionService', function (require) {
    "use strict";

    var Class = require('web.Class');

    var EventBus = Class.extend({
        init: function () {
            this.listeners = {};
        },
        on: function (event, callback) {
            if (!this.listeners[event]) {
                this.listeners[event] = [];
            }
            this.listeners[event].push(callback);
        },
        trigger: function (event, data) {
            if (this.listeners[event]) {
                this.listeners[event].forEach(function (callback) {
                    callback(data);
                });
            }
        }
    });

    var HeartbeatConnectionService = Class.extend({
        init: function (url, baseInterval, maxInterval, backoffFactor) {
            this.url = url;
            this.baseInterval = baseInterval || 1000;
            this.maxInterval = maxInterval || 1000*60*60;
            this.backoffFactor = backoffFactor || 2;
            this.retryCount = 0;
            this.connection = null;
            this.connectionStatus = 'closed';
            this.bus = new EventBus();
        },

        setupConnection: function () {
            if (this.connection) return;

            console.log("Initializing connection with heartbeat check...");
            this.connectionStatus = 'connecting';
            this.connection = new WebSocket(this.url);

            this.connection.onopen = this._onOpen.bind(this);
            this.connection.onmessage = this._onMessage.bind(this);
            this.connection.onerror = this._onError.bind(this);
            this.connection.onclose = this._onClose.bind(this);
        },

        _onOpen: function () {
            console.log("Connection established.");
            this.retryCount = 0;
            this.connectionStatus = 'open';
            this.bus.trigger("onopen");
        },

        _onMessage: function (event) {
            console.log("Heartbeat received: ", event.data);
            this.bus.trigger("onmessage", event);
        },

        _onError: function (event) {
            console.log("Error observed in connection:", event);
            this.connectionStatus = 'error';
            this.closeConnection();
            this.bus.trigger("onerror", event);
        },

        _onClose: function (event) {
            console.log("Connection closed.");
            this.connectionStatus = 'closed';
            this.closeConnection();
            this.bus.trigger("onclose", event);
            this.reconnect();
        },

        reconnect: function () {
            var delay = Math.min(this.baseInterval * Math.pow(this.backoffFactor, this.retryCount), this.maxInterval);
            console.log("Scheduling reconnect in " + delay + " ms");
            setTimeout(this.setupConnection.bind(this), delay);
            this.retryCount++;
        },

        closeConnection: function () {
            if (this.connection) {
                this.connection.close();
                this.connection = null;
                this.connectionStatus = 'closed';
            }
        },

        isAlive: function () {
            return this.connectionStatus === 'open';
        }
    });

    return HeartbeatConnectionService;
});


odoo.define('omni_print.heartbeat_service', function (require) {
    "use strict";

    var HeartbeatConnectionService = require('omni_print.HeartbeatConnectionService');
    var ajax = require('web.ajax');

    var service = null;

    function initService() {
        if (service) {
            return Promise.resolve(service);
        }

        return ajax.rpc('/web/dataset/call_kw/ir.config_parameter/get_param', {
            model: 'ir.config_parameter',
            method: 'get_param',
            args: ['omni_print.websocket_url', 'ws://127.0.0.1:32276/ping'],
            kwargs: {},
        }).then(function(websocket_url) {
            service = new HeartbeatConnectionService(websocket_url);
            service.setupConnection();
            return service;
        });
    }

    return initService();
});
