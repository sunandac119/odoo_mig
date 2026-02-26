odoo.define('pos_multi_uom_barcode.ChangeUoM', function(require) {
    'use strict';
    const PosComponent = require('point_of_sale.PosComponent');
    const Registries = require('point_of_sale.Registries');

    var models = require('point_of_sale.models');

    models.load_fields("product.product", ["barcode_uom_ids"]);

    var _super_orderline = models.Orderline.prototype;
    var _super_product = models.Product.prototype;
    models.Orderline = models.Orderline.extend({
        initialize: function(attr, options) {
            _super_orderline.initialize.call(this,attr,options);
            this.product_uom_id = this.product_uom_id || this.product.uom_id[0]
        },
        init_from_JSON: function(json){
            _super_orderline.init_from_JSON.apply(this,arguments);
            this.product_uom_id = json.product_uom_id;
        },
        export_as_JSON: function() {
            var json = _super_orderline.export_as_JSON.call(this);
            json.product_uom_id = this.product_uom_id[0];
            return json;
        },
        set_custom_uom_id: function(product_uom_id){
            this.product_uom_id = product_uom_id;
            this.trigger('change',this);
        },
        get_custom_unit: function(){
            return this.product_uom_id;
        },
        get_unit: function(){
            var res = _super_orderline.get_unit.call(this);
            var product_uom_id = this.product_uom_id;
            if(!product_uom_id){
                return res;
            }
            product_uom_id = product_uom_id[0] || product_uom_id;
            if(!this.pos){
                return undefined;
            }
            return this.pos.units_by_id[product_uom_id];
        },
        find_reference_unit_price: function(product, product_uom){
            if(product_uom.uom_type == 'reference'){
                return product.lst_price;
            }
            else if(product_uom.uom_type == 'smaller'){
               return (product.lst_price * product_uom.factor);
            }
            else if(product_uom.uom_type == 'bigger'){
               return (product.lst_price / product_uom.factor_inv);
            }
        },
        get_latest_price: function(uom, product, ref_price, product_uom, uom_list){
            var ref_unit = null;
            for (var i in uom_list){
                if(uom_list[i].item.uom_type == 'reference'){
                    ref_unit = uom_list[i];
                    break;
                }
            }
            if(ref_unit){
                if(uom.uom_type == 'bigger'){
                    return (ref_price * uom.factor_inv);
                }
                else if(uom.uom_type == 'smaller'){
                    return (ref_price / uom.factor);
                }
                else if(uom.uom_type == 'reference'){
                    return ref_price;
                }
            }
            return product.lst_price;
        },
        // export_for_printing: function() {
        //     var line = _super_orderline.export_for_printing.apply(this,arguments);
        //     line.unit_name = this.get_unit().name;
        //     console.log("====line.unit_name",line.unit_name)
        //     console.log("====this.product_uom_id",line.unit_name)
        //     return line;
        // },
    });
    models.Product = models.Product.extend({
        initialize: function(attr, options) {
            _super_product.initialize.call(this,attr,options);
        },
        
        get_price: function(pricelist, quantity, price_extra){
            var self = this;
            var date = moment();

            // In case of nested pricelists, it is necessary that all pricelists are made available in
            // the POS. Display a basic alert to the user in this case.
            if (pricelist === undefined) {
                return;
            }

            var category_ids = [];
            var category = this.categ;
            while (category) {
                category_ids.push(category.id);
                category = category.parent;
            }
            var pricelist_items = _.filter(pricelist.items, function (item) {
                return (item.x_scanned_barcode === self.barcode) &&
                       (! item.date_start || moment.utc(item.date_start).isSameOrBefore(date)) &&
                       (! item.date_end || moment.utc(item.date_end).isSameOrAfter(date));

            });
                // return (! item.product_tmpl_id || item.product_tmpl_id[0] === self.product_tmpl_id) &&
                //        (! item.product_id || item.product_id[0] === self.id) &&
                //        (! item.uom_id || item.uom_id[0] === (self.uom_id[0] || self.temp_uom_id)) &&
                //        (! item.categ_id || _.contains(category_ids, item.categ_id[0])) &&
                //        (! item.date_start || moment.utc(item.date_start).isSameOrBefore(date)) &&
                //        (! item.date_end || moment.utc(item.date_end).isSameOrAfter(date));

            var price = self.lst_price;
            if (price_extra){
                price += price_extra;
            }
            _.find(pricelist_items, function (rule) {
                if (rule.min_quantity && quantity < rule.min_quantity) {
                    return false;
                }

                if (rule.base === 'pricelist') {
                    price = self.get_price(rule.base_pricelist, quantity);
                } else if (rule.base === 'standard_price') {
                    price = self.standard_price;
                }

                if (rule.compute_price === 'fixed') {
                    price = rule.fixed_price;
                    return true;
                } else if (rule.compute_price === 'percentage') {
                    price = price - (price * (rule.percent_price / 100));
                    return true;
                } else {
                    var price_limit = price;
                    price = price - (price * (rule.price_discount / 100));
                    if (rule.price_round) {
                        price = round_pr(price, rule.price_round);
                    }
                    if (rule.price_surcharge) {
                        price += rule.price_surcharge;
                    }
                    if (rule.price_min_margin) {
                        price = Math.max(price, price_limit + rule.price_min_margin);
                    }
                    if (rule.price_max_margin) {
                        price = Math.min(price, price_limit + rule.price_max_margin);
                    }
                    return true;
                }

                return false;
            });

            // for(let line of self.barcode_lines)
            // {
            //     if(line.uom_id[0] == self.temp_uom_id) {
            //         price = line.sale_price;
            //         break;
            //     }
            // }

            // This return value has to be rounded with round_di before
            // being used further. Note that this cannot happen here,
            // because it would cause inconsistencies with the backend for
            // pricelist that have base == 'pricelist'.
            return price;
        },
    });

    class ChangeUoM extends PosComponent {
       async changeUoM() {
         const order = this.env.pos.get_order();
            if(order) {
                if (order.selected_orderline) {
                    const PosUomList = []
                    const order_line = order.selected_orderline
                    const product = order_line.get_product()
                    for (let unit of this.env.pos.units) {
                        for(let pos_line of order_line.get_product().barcode_lines){
                            if (pos_line.uom_id[0] == unit.id){
                                PosUomList.push({
                                    id: unit.id,
                                    label: unit.name,
                                    item: unit,
                                });
                            }
                        }

                    }
                     const { confirmed, payload: selectedUomId } = await this.showPopup(
                        'SelectionPopup',
                        {
                            title: 'Select UOM',
                            list: PosUomList,
                        }
                    );
                    if (confirmed) {
                        const product_uom = order_line.get_unit();

                        var latest_price = order_line.get_product().lst_price;
                        for(let line of order_line.get_product().barcode_lines)
                        {
                            if(line.uom_id[0] == selectedUomId.id) {
                                latest_price = line.sale_price;
                                break;
                            }
                        }
                        order_line.product_uom_id = [selectedUomId.id, selectedUomId.name];
                        // order_line.set_unit_price(latest_price);
                        order_line.product.temp_uom_id = selectedUomId.id
                        order_line.set_unit_price(order_line.product.get_price(order_line.order.pricelist, order_line.get_quantity()));
                        delete order_line.product.temp_uom_id;
                        // order_line.price = latest_price;
                    }
                }
            }
        }
    }
    ChangeUoM.template = 'ChangeUoM';
    Registries.Component.add(ChangeUoM);

    return ChangeUoM;
});
