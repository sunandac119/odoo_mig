odoo.define("sh_pos_order_list.screen", function (require) {
    "use strict";

    const { debounce } = owl.utils;
    const PosComponent = require("point_of_sale.PosComponent");
    const Registries = require("point_of_sale.Registries");
    const { useListener } = require("web.custom_hooks");
    const rpc = require("web.rpc");
    var core = require("web.core");
    var framework = require("web.framework");
    var QWeb = core.qweb;
    const PaymentScreen = require("point_of_sale.PaymentScreen");
    const { posbus } = require("point_of_sale.utils");
    var field_utils = require("web.field_utils");

    const PosReturnPaymentScreen = (PaymentScreen) =>
        class extends PaymentScreen {
            async _finalizeValidation() {
                super._finalizeValidation();
                this.env.pos.order_length = this.env.pos.order_length + 1;
            }
        };
    Registries.Component.extend(PaymentScreen, PosReturnPaymentScreen);

    class OrderListScreen extends PosComponent {
        constructor() {
            super(...arguments);
            this.filter_by_paid_order = false;
            this.filter_by_invoice_order = false;
            this.filter_by_draft_order = false;
            this.filter_by_posted_order = false;
            this.paid_orders = []
            this.state = {
                query: null,
                selectedTemplate: this.props.template,
            };
            this.updateTemplateList = debounce(this.updateTemplateList, 70);
            if (this.env.pos.db.all_order.length > 0) {
                var today = new Date();
                var dd = today.getDate();
                var mm = today.getMonth() + 1;
                var yyyy = today.getFullYear();
                var today_date = yyyy + "-" + mm + "-" + dd;
                if (this.env.pos.config.sh_load_order_by == "day_wise") {
                    if (this.env.pos.config.sh_day_wise_option == "current_day") {
                        this.env.pos.db.all_order = this.env.pos.get_current_day_order(this.env.pos.db.all_order);
                    } else if (this.env.pos.config.sh_day_wise_option == "last_no_day") {
                        if (this.env.pos.config.sh_last_no_days != 0) {
                            this.env.pos.db.all_order = this.env.pos.get_last_day_order(this.env.pos.db.all_order);
                        }
                    }
                } else if (this.env.pos.config.sh_load_order_by == "session_wise") {
                    if (this.env.pos.config.sh_session_wise_option == "current_session") {
                        this.env.pos.db.all_order = this.env.pos.get_current_session_order(this.env.pos.db.all_order);
                    } else if (this.env.pos.config.sh_session_wise_option == "last_no_session") {
                        if (this.env.pos.config.sh_last_no_session != 0) {
                            this.env.pos.db.all_order = this.env.pos.get_last_session_order(this.env.pos.db.all_order);
                        }
                    }
                }
            }
        }
        back() {
            this.trigger("close-temp-screen");
        }
        sh_paid_order_filter() {
            if ($('.sh_paid_order').hasClass('highlight')) {
                this.filter_by_paid_order = false
                $('.sh_paid_order').removeClass('highlight')
            } else {
                $('.sh_filter_buttons').find('button').removeClass('highlight')
                this.filter_by_paid_order = true
                this.filter_by_posted_order = false
                this.filter_by_invoice_order = false
                $('.sh_paid_order').addClass('highlight')
                $('.sh_posted_order').removeClass('highlight')
                $('.sh_invoiced_order').removeClass('highlight')
            }
            $(".sh_pagination").pagination("selectPage", 1);
            this.render()
        }
        sh_posted_order_filter() {

            if ($('.sh_posted_order').hasClass('highlight')) {
                this.filter_by_posted_order = false
                $('.sh_posted_order').removeClass('highlight')
            } else {
                this.filter_by_posted_order = true
                this.filter_by_paid_order = false
                this.filter_by_invoice_order = false
                $('.sh_filter_buttons').find('button').removeClass('highlight')
                $('.sh_posted_order').addClass('highlight')
                $('.sh_paid_order').removeClass('highlight')
                $('.sh_invoiced_order').removeClass('highlight')
            }
            $(".sh_pagination").pagination("selectPage", 1);
            this.render()
        }
        sh_invoiced_order_filter() {

            if ($('.sh_invoiced_order').hasClass('highlight')) {
                this.filter_by_invoice_order = false
                $('.sh_invoiced_order').removeClass('highlight')
            } else {
                this.filter_by_invoice_order = true
                this.filter_by_paid_order = false
                this.filter_by_posted_order = false
                $('.sh_filter_buttons').find('button').removeClass('highlight')
                $('.sh_invoiced_order').addClass('highlight')
                $('.sh_posted_order').removeClass('highlight')
                $('.sh_paid_order').removeClass('highlight')
            }
            $(".sh_pagination").pagination("selectPage", 1);
            this.render()
        }
        sh_refresh_page(){
            this.mounted()
            this.render()
        }
        get_order_by_state(name) {
            var self = this;
            var templates = []
            templates = _.filter(self.env.pos.db.all_display_order, function (template) {
                if (template["state"].indexOf(name) > -1) {
                    return true;
                } else {
                    return false;
                }
            });
            
            if(this.env.pos.config.sh_load_order_by && this.env.pos.config.sh_load_order_by == 'all'){                    	
            	return templates;
            }else if (self.env.pos.config.sh_load_order_by == "session_wise") {
            	if (self.env.pos.config.sh_session_wise_option == "current_session") {                    		
            		return templates.filter(function (order) {
            			return order.session_id[0] == self.env.pos.pos_session.id;
            		});                    	
            	}else if (self.env.pos.config.sh_session_wise_option == "last_no_session") {
                    if (self.env.pos.config.sh_last_no_session != 0) {
                    	var filter_order = []
                        filter_order = self.env.pos.get_last_session_order(templates);
                        return filter_order
                    }else{
                    	return []
                    }
                }
            }else if (self.env.pos.config.sh_load_order_by == "day_wise") {
            	if (self.env.pos.config.sh_day_wise_option == "current_day") {                    		
            		return templates.filter(function (order) {
                        var date = new Date();
                        var today_date = date.getFullYear() + "-" + ("0" + (date.getMonth() + 1)).slice(-2) + "-" + ("0" + date.getDate()).slice(-2);
                        return order.date_order.split(" ")[0] === today_date;
                    });
            		
                } else if (self.env.pos.config.sh_day_wise_option == "last_no_day") {
                    if (self.env.pos.config.sh_last_no_days != 0) {
                  	  return templates.filter(function (order) {
                            var date = new Date();
                            var last = new Date(date.getTime() - self.env.pos.config.sh_last_no_days * 24 * 60 * 60 * 1000);
                            var last = last.getFullYear() + "-" + ("0" + (last.getMonth() + 1)).slice(-2) + "-" + ("0" + last.getDate()).slice(-2);
                            var today_date = date.getFullYear() + "-" + ("0" + (date.getMonth() + 1)).slice(-2) + "-" + ("0" + date.getDate()).slice(-2);
                            
                            var formated_last_date = field_utils.format.datetime(moment(last), {}, { timezone: false });
                            var formated_today_date = field_utils.format.datetime(moment(today_date), {}, { timezone: false });
                            
                            if(order.date_order.split(" ")[0] > last && order.date_order.split(" ")[0] <= today_date){
                            	return order
                            }else if(order.date_order.split(" ")[0] > formated_last_date && order.date_order.split(" ")[0] <= formated_today_date){
                            	return order
                            }
                            
                        });
                    }else{
                  	  return []
                    }
                }                       	
            }
        }
        change_date() {
            this.state.query = $("#date1")[0].value;
            this.render();
        }
        updateOrderList(event) {
            this.state.query = event.target.value;
            const serviceorderlistcontents = this.posorderdetail;
            if (event.code === "Enter" && serviceorderlistcontents.length === 1) {
                this.state.selectedQuotation = serviceorderlistcontents[0];
            } else {
                this.render();
            }
        }
        get posorderdetail() {
            var self = this
            var AllIds = _.map(self.env.pos.db.all_display_order, function (display_order) {
                return display_order.id
            })
            var new_orders = self.env.pos.db.all_order.filter(order =>  !AllIds.includes(order.id)   )
                    
            if (new_orders && new_orders.length){
                for (var neworder of new_orders){
                    self.env.pos.db.all_display_order.unshift(neworder)
                }
            }
            if (this.filter_by_paid_order) {
                if (this.state.query && this.state.query.trim() !== "") {
                    var templates = this.get_order_by_paid_order(this.state.query.trim());
                    $(".sh_pagination").pagination("updateItems", Math.ceil(templates.length / self.env.pos.config.sh_how_many_order_per_page));
                    var current_page = $(".sh_pagination").find('.active').text();

                    var showFrom = parseInt(self.env.pos.config.sh_how_many_order_per_page) * (parseInt(current_page) - 1);;
                    var showTo = showFrom + parseInt(self.env.pos.config.sh_how_many_order_per_page);
                    templates = templates.slice(showFrom, showTo);
                    return templates;
                } else {
                    var templates = this.get_order_by_state('paid');

                    $(".sh_pagination").pagination("updateItems", Math.ceil(templates.length / self.env.pos.config.sh_how_many_order_per_page));

                    var current_page = $(".sh_pagination").find('.active').text();

                    var showFrom = parseInt(self.env.pos.config.sh_how_many_order_per_page) * (parseInt(current_page) - 1);
                    var showTo = showFrom + parseInt(self.env.pos.config.sh_how_many_order_per_page);
                    templates = templates.slice(showFrom, showTo);
                    return templates
                }
            } else if (this.filter_by_invoice_order) {
                if (this.state.query && this.state.query.trim() !== "") {
                    var templates = this.get_order_by_invoiced_order(this.state.query.trim());
                    $(".sh_pagination").pagination("updateItems", Math.ceil(templates.length / self.env.pos.config.sh_how_many_order_per_page));
                    var current_page = $(".sh_pagination").find('.active').text();
                    var showFrom = parseInt(self.env.pos.config.sh_how_many_order_per_page) * (parseInt(current_page) - 1);;
                    var showTo = showFrom + parseInt(self.env.pos.config.sh_how_many_order_per_page);
                    templates = templates.slice(showFrom, showTo);
                    return templates
                    
                } else {
                    var templates = this.get_order_by_state('invoiced');

                    $(".sh_pagination").pagination("updateItems", Math.ceil(templates.length / self.env.pos.config.sh_how_many_order_per_page));

                    var current_page = $(".sh_pagination").find('.active').text();
                    var showFrom = parseInt(self.env.pos.config.sh_how_many_order_per_page) * (parseInt(current_page) - 1);
                    var showTo = showFrom + parseInt(self.env.pos.config.sh_how_many_order_per_page);
                    templates = templates.slice(showFrom, showTo);
                    return templates;
                }

            } else if (this.filter_by_posted_order) {
                if (this.state.query && this.state.query.trim() !== "") {
                    var templates = this.get_order_by_posted_order(this.state.query.trim());
                    $(".sh_pagination").pagination("updateItems", Math.ceil(templates.length / self.env.pos.config.sh_how_many_order_per_page));
                    var current_page = $(".sh_pagination").find('.active').text();
                    var showFrom = parseInt(self.env.pos.config.sh_how_many_order_per_page) * (parseInt(current_page) - 1);;
                    var showTo = showFrom + parseInt(self.env.pos.config.sh_how_many_order_per_page);
                    templates = templates.slice(showFrom, showTo);
                    return templates;
                } else {
                    var templates = this.get_order_by_state('done');

                    $(".sh_pagination").pagination("updateItems", Math.ceil(templates.length / self.env.pos.config.sh_how_many_order_per_page));

                    var current_page = $(".sh_pagination").find('.active').text();
                    var showFrom = parseInt(self.env.pos.config.sh_how_many_order_per_page) * (parseInt(current_page) - 1);
                    var showTo = showFrom + parseInt(self.env.pos.config.sh_how_many_order_per_page);
                    templates = templates.slice(showFrom, showTo);
                    return templates;
                }
            }else {
                if (this.state.query && this.state.query.trim() !== "") {
                    var templates = this.get_order_by_name(this.state.query.trim());
                    $(".sh_pagination").pagination("updateItems", Math.ceil(templates.length / self.env.pos.config.sh_how_many_order_per_page));
                    var showFrom = 0;
                    var showTo = showFrom + parseInt(self.env.pos.config.sh_how_many_order_per_page);
                    templates = templates.slice(showFrom, showTo);
                    return templates;
                } else {
                    if ($(".sh_pagination") && $(".sh_pagination").length) {                    	
                    	
                    	if(this.env.pos.config.sh_load_order_by && this.env.pos.config.sh_load_order_by == 'all'){                    	
                    		$(".sh_pagination").pagination("updateItems", Math.ceil(self.env.pos.order_length / self.env.pos.config.sh_how_many_order_per_page));
                        }else if (self.env.pos.config.sh_load_order_by == "session_wise") {
                        	if (self.env.pos.config.sh_session_wise_option == "current_session") {                    		
                        		var display_order= []
                        		display_order = self.env.pos.db.all_display_order.filter(function (order) {
                        			return order.session_id[0] == self.env.pos.pos_session.id;
                        		});
                        		$(".sh_pagination").pagination("updateItems", Math.ceil(display_order.length / self.env.pos.config.sh_how_many_order_per_page));
                        	}else if (self.env.pos.config.sh_session_wise_option == "last_no_session") {
                                if (self.env.pos.config.sh_last_no_session != 0) {
                                	var filter_order = []
                                    filter_order = self.env.pos.get_last_session_order(self.env.pos.db.all_display_order);
                                	$(".sh_pagination").pagination("updateItems", Math.ceil(filter_order.length / self.env.pos.config.sh_how_many_order_per_page));
                                }else{
                                	$(".sh_pagination").pagination("updateItems", 1);
                                }
                            }
                        }else if (self.env.pos.config.sh_load_order_by == "day_wise") {
                        	if (self.env.pos.config.sh_day_wise_option == "current_day") {
                        		var display_order = []
                        		display_order = self.env.pos.db.all_display_order.filter(function (order) {
                                    var date = new Date();
                                    var today_date = date.getFullYear() + "-" + ("0" + (date.getMonth() + 1)).slice(-2) + "-" + ("0" + date.getDate()).slice(-2);
                                    return order.date_order.split(" ")[0] === today_date;
                                });
                        		$(".sh_pagination").pagination("updateItems", Math.ceil(display_order.length / self.env.pos.config.sh_how_many_order_per_page));
                            } else if (self.env.pos.config.sh_day_wise_option == "last_no_day") {
                                if (self.env.pos.config.sh_last_no_days != 0) {
                                	var display_order = []
                                	display_order = self.env.pos.db.all_display_order.filter(function (order) {
                                        var date = new Date();
                                        var last = new Date(date.getTime() - self.env.pos.config.sh_last_no_days * 24 * 60 * 60 * 1000);
                                        var last = last.getFullYear() + "-" + ("0" + (last.getMonth() + 1)).slice(-2) + "-" + ("0" + last.getDate()).slice(-2);
                                        var today_date = date.getFullYear() + "-" + ("0" + (date.getMonth() + 1)).slice(-2) + "-" + ("0" + date.getDate()).slice(-2);
                                        
                                        var formated_last_date = field_utils.format.datetime(moment(last), {}, { timezone: false });
                                        var formated_today_date = field_utils.format.datetime(moment(today_date), {}, { timezone: false });
                                        
                                        if(order.date_order.split(" ")[0] > last && order.date_order.split(" ")[0] <= today_date){
                                        	return order
                                        }else if(order.date_order.split(" ")[0] > formated_last_date && order.date_order.split(" ")[0] <= formated_today_date){
                                        	return order
                                        }
                                        
                                    });
                                	$(".sh_pagination").pagination("updateItems", Math.ceil(display_order.length / self.env.pos.config.sh_how_many_order_per_page));
                                }else{
                                	$(".sh_pagination").pagination("updateItems", 1);
                                }
                            }                       	
                        }
                    }
                    return this.env.pos.db.all_order;
                }
            }
        }
        get_order_by_invoiced_order(name) {
            var self = this;
            return _.filter(this.get_order_by_state('invoiced'), function (template) {
                if (template.name.indexOf(name) > -1) {
                    return true;
                } else if (template["pos_reference"].indexOf(name) > -1) {
                    return true;
                } else if (template["partner_id"] && template["partner_id"][1] && template["partner_id"][1].toLowerCase().indexOf(name) > -1) {
                    return true;
                } else if (template["date_order"] && template["date_order"].indexOf(name) > -1) {
                    return true;
                } else {
                    return false;
                }
            });
        }
        get_order_by_posted_order(name) {
            var self = this;
            return _.filter(this.get_order_by_state('done'), function (template) {
                if (template.name.indexOf(name) > -1) {
                    return true;
                } else if (template["pos_reference"].indexOf(name) > -1) {
                    return true;
                } else if (template["partner_id"] && template["partner_id"][1] && template["partner_id"][1].toLowerCase().indexOf(name) > -1) {
                    return true;
                } else if (template["date_order"] && template["date_order"].indexOf(name) > -1) {
                    return true;
                } else {
                    return false;
                }
            });
        }
        get_order_by_paid_order(name) {
            var self = this;
            return _.filter(this.get_order_by_state('paid'), function (template) {
                if (template.name.indexOf(name) > -1) {
                    return true;
                } else if (template["pos_reference"].indexOf(name) > -1) {
                    return true;
                } else if (template["partner_id"] && template["partner_id"][1] && template["partner_id"][1].toLowerCase().indexOf(name) > -1) {
                    return true;
                } else if (template["date_order"] && template["date_order"].indexOf(name) > -1) {
                    return true;
                } else {
                    return false;
                }
            });
        }
        get_order_by_name(name) {
            var self = this;
            return _.filter(self.env.pos.db.all_display_order, function (template) {
                if (template.name.indexOf(name) > -1) {
                    return true;
                } else if (template["pos_reference"].indexOf(name) > -1) {
                    return true;
                } else if (template["partner_id"] && template["partner_id"][1] && template["partner_id"][1].toLowerCase().indexOf(name) > -1) {
                    return true;
                } else if (template["date_order"] && template["date_order"].indexOf(name) > -1) {
                    return true;
                } else {
                    return false;
                }
            });
        }
        clickLine(event) {
            var self = this;
            self.hasclass = true;
            if ($(event.currentTarget).hasClass("highlight")) {
                self.hasclass = false;
            }
            $(".sh_order_list .highlight").removeClass("highlight");
            $(event.currentTarget).closest("table").find(".show_order_detail").removeClass("show_order_detail");
            $(event.currentTarget).closest("table").find(".show_order_detail").removeClass("show_order_detail");
            $(event.currentTarget).closest("table").find(".show_order_detail").removeClass("show_order_detail");
            var order_id = $(event.currentTarget).data("id");
            if (!order_id) {
                order_id = $(event.currentTarget).attr("data-order-id");
            }
            var order_data = self.env.pos.db.order_by_uid[order_id];
            if (!order_data) {
                order_data = self.env.pos.db.order_by_id[order_id];
            }
            if (order_data && self.hasclass) {
                self.selected_pos_order = order_id;

                if (order_data.sh_line_id) {
                    _.each(order_data.sh_line_id, function (pos_order_line) {
                        $(event.currentTarget).addClass("highlight");
                        $(event.currentTarget)
                            .closest("table")
                            .find("tr#" + order_data.pos_reference.split(" ")[1])
                            .addClass("show_order_detail");
                        $(event.currentTarget)
                            .closest("table")
                            .find("#" + pos_order_line)
                            .addClass("show_order_detail");
                    });
                } else {
                    _.each(order_data.lines, function (pos_order_line) {
                        $(event.currentTarget).addClass("highlight");
                        $(event.currentTarget)
                            .closest("table")
                            .find("tr#" + order_data.pos_reference.split(" ")[1])
                            .addClass("show_order_detail");
                        $(event.currentTarget)
                            .closest("table")
                            .find("#" + self.env.pos.db.order_line_by_id[pos_order_line].id)
                            .addClass("show_order_detail");
                    });
                }
            }
        }
        reorder_pos_order(event) {
            var self = this;
            var order_id = event.currentTarget.closest("tr").attributes[0].value;

            var order_data = self.env.pos.db.order_by_uid[order_id];
            if (!order_data) {
                order_data = self.env.pos.db.order_by_id[order_id];
            }
            var order_line = [];

            if (self.env.pos.get_order() && self.env.pos.get_order().get_orderlines() && self.env.pos.get_order().get_orderlines().length > 0) {
                var orderlines = self.env.pos.get_order().get_orderlines();
                _.each(orderlines, function (each_orderline) {
                    if (self.env.pos.get_order().get_orderlines()[0]) {
                        self.env.pos.get_order().remove_orderline(self.env.pos.get_order().get_orderlines()[0]);
                    }
                });
            }

            var current_order = self.env.pos.get_order();

            _.each(order_data.lines, function (each_order_line) {
                var line_data = self.env.pos.db.order_line_by_id[each_order_line];
                if (!line_data) {
                    line_data = self.env.pos.db.order_line_by_uid[each_order_line[2].sh_line_id];
                }
                var product = self.env.pos.db.get_product_by_id(line_data.product_id[0]);
                if (!product) {
                    product = self.env.pos.db.get_product_by_id(line_data.product_id);
                }
                if (product) {
                    current_order.add_product(product, {
                        quantity: line_data.qty,
                        price: line_data.price_unit,
                        discount: line_data.discount,
                    });
                }
            });
            if (order_data.partner_id[0]) {
                self.env.pos.get_order().set_client(self.env.pos.db.get_partner_by_id(order_data.partner_id[0]));
            }
            current_order.assigned_config = order_data.assigned_config;
            self.trigger("close-temp-screen");
        }

		print_pos_order(event) {
			const self = this;
			const tr = event.currentTarget.closest("tr");

			const order_id =
				tr.getAttribute("data-id") ||
				tr.getAttribute("data-order-id");

			const order_data =
				self.env.pos.db.order_by_uid[order_id] ||
				self.env.pos.db.order_by_id[order_id];

			if (!order_data) return;

			const current_order = self.env.pos.get_order();

			/* 1️⃣ Clear order */
			while (current_order.get_orderlines().length) {
				current_order.remove_orderline(
					current_order.get_orderlines()[0]
				);
			}

			/* 2️⃣ Restore lines (NO merge, NO loyalty trigger) */
			_.each(order_data.lines, function (line_id) {
				const line =
					self.env.pos.db.order_line_by_id[line_id];

				if (!line) return;

				const product =
					self.env.pos.db.get_product_by_id(
						line.product_id[0] || line.product_id
					);

				if (!product) return;

				current_order.add_product(product, {
					quantity: line.qty,
					price: line.price_unit,
					discount: line.discount,
					merge: false,
				});
			});

			/* 3️⃣ Restore customer */
			let partner = null;
			if (order_data.partner_id && order_data.partner_id[0]) {
				partner = self.env.pos.db.get_partner_by_id(
					order_data.partner_id[0]
				);
				if (partner) current_order.set_client(partner);
			}

			/* 4️⃣ REPRINT FLAGS */
			current_order.name = order_data.pos_reference;
			current_order.is_reprint = true;

			/* 5️⃣ 🔑 Inject loyalty FROM DB */
			current_order.loyalty_points = order_data.loyalty_points || 0;
			current_order.loyalty_spent = order_data.loyalty_spent || 0;

			/* 6️⃣ Go to receipt */
			self.trigger("close-temp-screen");
			self.showScreen("ReceiptScreen");
		}
        
        mounted() {
            var self = this;
            if (!this.filter_by_paid_order && !this.filter_by_invoice_order && !this.filter_by_posted_order) {
                $(".sh_pagination").pagination({
                    pages: Math.ceil(self.env.pos.order_length / self.env.pos.config.sh_how_many_order_per_page),
                    displayedPages: 1,
                    edges: 1,
                    cssStyle: "light-theme",
                    showPageNumbers: false,
                    showNavigator: true,
                    onPageClick: function (pageNumber) {
                        try {
                            rpc.query({
                                model: "pos.order",
                                method: "search_order",
                                args: [self.env.pos.config, pageNumber + 1],
                            })
                                .then(function (orders) {
                                    if (orders) {
                                        if (orders["order"].length == 0) {
                                            $($(".next").parent()).addClass("disabled");
                                            $(".next").replaceWith(function () {
                                                $("<span class='current next'>Next</span>");
                                            });
                                        }
                                    }
                                })
                                .catch(function (reason) {
                                    var showFrom = parseInt(self.env.pos.config.sh_how_many_order_per_page) * (parseInt(pageNumber + 1) - 1);
                                    var showTo = showFrom + parseInt(self.env.pos.config.sh_how_many_order_per_page);
                                    self.env.pos.db.all_order = self.env.pos.db.all_order_temp.slice(showFrom, showTo);
                                    if (self.env.pos.db.all_order && self.env.pos.db.all_order.length == 0) {
                                        $($(".next").parent()).addClass("disabled");
                                        $(".next").replaceWith(function () {
                                            $("<span class='current next'>Next</span>");
                                        });
                                    }
                                });

                            rpc.query({
                                model: "pos.order",
                                method: "search_order",
                                args: [self.env.pos.config, pageNumber],
                            })
                                .then(function (orders) {
                                    self.env.pos.db.all_order = [];
                                    self.env.pos.db.order_by_id = {};

                                    if (orders) {
                                        if (orders["order"]) {
                                            self.env.pos.db.all_orders(orders["order"]);
                                        }
                                        if (orders["order_line"]) {
                                            self.env.pos.db.all_orders_line(orders["order_line"]);
                                        }
                                    }
                                    self.all_order = self.env.pos.db.all_order;

                                    self.render();
                                })
                                .catch(function (reason) {
                                    var showFrom = parseInt(self.env.pos.config.sh_how_many_order_per_page) * (parseInt(pageNumber) - 1);
                                    var showTo = showFrom + parseInt(self.env.pos.config.sh_how_many_order_per_page);
                                    self.env.pos.db.all_order = self.env.pos.db.all_order_temp.slice(showFrom, showTo);
                                    self.render();
                                });
                        } catch (error) { }
                    },
                });
            }
            super.mounted();
            $(".sh_pagination").pagination("selectPage", 1);
        }
    }
    OrderListScreen.template = "OrderListScreen";
    Registries.Component.add(OrderListScreen);

    return OrderListScreen;
});
