# -*- coding: utf-8 -*-
##############################################################################
#
# Copyright 2019 EquickERP
#
##############################################################################

import pytz
import time
from operator import itemgetter
from itertools import groupby
from odoo import models, fields, api
from odoo.tools import DEFAULT_SERVER_DATETIME_FORMAT, float_round
from datetime import datetime, date, timedelta

class wt_inventory_valuation_report_inventory_valuation_report(models.AbstractModel):
    _name = 'report.wt_inventory_valuation_report.inventory_valuation_report'

    @api.model
    def _get_report_values(self, docids, data=None):
        report = self.env['ir.actions.report']._get_report_from_name('wt_inventory_valuation_report.inventory_valuation_report')
        record_id = data['form']['id'] if data and data['form'] and data['form']['id'] else docids[0]
        records = self.env['wizard.inventory.valuation'].browse(record_id)
        return {
           'doc_model': report.model,
           'docs': records,
           'data': data,
           'get_beginning_inventory': self._get_beginning_inventory,
           'get_products':self._get_products,
           'get_product_sale_qty':self.get_product_sale_qty,
           'get_location_wise_product':self.get_location_wise_product,
           'get_warehouse_wise_location':self.get_warehouse_wise_location,
           'get_product_valuation':self.get_product_valuation,
           'get_product_sale_qtyy': self.get_product_sale_qtyy,
           'get_beginning_inventoryy': self._get_beginning_inventoryy
        }

    def get_warehouse_wise_location(self, record, warehouse):
        stock_location_obj = self.env['stock.location']
        location_ids = stock_location_obj.search([('location_id', 'child_of', warehouse.view_location_id.id)])
        final_location_ids = record.location_ids & location_ids
        return final_location_ids or location_ids

    def get_location_wise_product(self, record, warehouse, product, location_ids, product_categ_id=None):
        group_by_location = {}
        begning_qty = product_qty_in = product_qty_out = product_qty_internal = product_qty_adjustment = ending_qty = product_ending_qty = 0.00
        for location in location_ids:
            group_by_location.setdefault(location, [])
            group_by_location[location].append(self._get_beginning_inventory(record, product, warehouse, [location.id]))
            get_product_sale_qty = self.get_product_sale_qty(record, warehouse, product, [location.id])
            location_begning_qty = group_by_location[location][0]

            group_by_location[location].append(get_product_sale_qty['product_qty_in'])
            group_by_location[location].append(get_product_sale_qty['product_qty_out'])
            group_by_location[location].append(get_product_sale_qty['product_qty_internal'])
            group_by_location[location].append(get_product_sale_qty['product_qty_adjustment'])
            ending_qty = location_begning_qty + get_product_sale_qty['product_qty_in'] + get_product_sale_qty['product_qty_out'] + get_product_sale_qty['product_qty_internal'] \
                + get_product_sale_qty['product_qty_adjustment']

            group_by_location[location].append(ending_qty)
            ending_qty = 0.00

            begning_qty += location_begning_qty
            product_qty_in += get_product_sale_qty['product_qty_in']
            product_qty_out += get_product_sale_qty['product_qty_out']
            product_qty_internal += get_product_sale_qty['product_qty_internal']
            product_qty_adjustment += get_product_sale_qty['product_qty_adjustment']

        product_ending_qty = begning_qty + product_qty_in + product_qty_out + product_qty_internal + product_qty_adjustment
        return group_by_location, [begning_qty, product_qty_in, product_qty_out, product_qty_internal, product_qty_adjustment, product_ending_qty]

    def get_location(self, records, warehouse):
        stock_location_obj = self.env['stock.location'].sudo()
        location_ids = []
        location_ids.append(warehouse.view_location_id.id)
        domain = [('company_id', '=', records.company_id.id), ('usage', '=', 'internal'), ('location_id', 'child_of', location_ids)]
        final_location_ids = stock_location_obj.search(domain).ids
        return final_location_ids

    def get_locationn(self, records, warehouses):
        stock_location_obj = self.env['stock.location'].sudo()
        location_ids = []
        for warehouse in warehouses:
            location_ids.append(warehouse.view_location_id.id)
        domain = [('company_id', '=', records.company_id.id), ('usage', '=', 'internal'), ('location_id', 'child_of', location_ids)]
        final_location_ids = stock_location_obj.search(domain).ids
        return final_location_ids

    def convert_withtimezone(self, userdate):
        timezone = pytz.timezone(self._context.get('tz') or 'UTC')
        if timezone:
            utc = pytz.timezone('UTC')
            end_dt = timezone.localize(fields.Datetime.from_string(userdate),is_dst=False)
            end_dt = end_dt.astimezone(utc)
            return end_dt.strftime(DEFAULT_SERVER_DATETIME_FORMAT)
        return userdate.strftime(DEFAULT_SERVER_DATETIME_FORMAT)

    def _get_products(self, record):
        product_product_obj = self.env['product.product']
        domain = [('type', '=', 'product')]
        product_ids = False
        if record.category_ids and record.filter_by == 'category':
            domain.append(('categ_id', 'in', record.category_ids.ids))
            product_ids = product_product_obj.search(domain)
        if record.product_ids and record.filter_by == 'product':
            product_ids = record.product_ids
        if not product_ids:
            product_ids = product_product_obj.search(domain)

        return product_ids

    def _get_beginning_inventory(self, record, product, warehouse, location=None):
        locations = location if location else self.get_location(record, warehouse)
        if isinstance(product, int):
            product_data = product
        else:
            product_data = product.id

        start_date = record.start_date
        from_date = self.convert_withtimezone(start_date)
        self._cr.execute(''' 
                        SELECT id as product_id,coalesce(sum(qty), 0.0) as qty
                        FROM
                            ((
                            SELECT pp.id, pp.default_code,m.date,
                                CASE when pt.uom_id = m.product_uom 
                                THEN u.name 
                                ELSE (select name from uom_uom where id = pt.uom_id) 
                                END AS name,

                                CASE when pt.uom_id = m.product_uom
                                THEN coalesce(sum(-m.product_qty)::decimal, 0.0)
                                ELSE coalesce(sum(-m.product_qty * pu.factor / u.factor )::decimal, 0.0) 
                                END AS qty

                            FROM product_product pp 
                            LEFT JOIN stock_move m ON (m.product_id=pp.id)
                            LEFT JOIN product_template pt ON (pp.product_tmpl_id=pt.id)
                            LEFT JOIN stock_location l ON (m.location_id=l.id)    
                            LEFT JOIN stock_picking p ON (m.picking_id=p.id)
                            LEFT JOIN uom_uom pu ON (pt.uom_id=pu.id)
                            LEFT JOIN uom_uom u ON (m.product_uom=u.id)
                            WHERE m.date <  %s AND (m.location_id in %s) AND m.state='done' AND pp.active=True AND pp.id = %s
                            GROUP BY  pp.id, pt.uom_id , m.product_uom ,pp.default_code,u.name,m.date
                            ) 
                            UNION ALL
                            (
                            SELECT pp.id, pp.default_code,m.date,
                                CASE when pt.uom_id = m.product_uom 
                                THEN u.name 
                                ELSE (select name from uom_uom where id = pt.uom_id) 
                                END AS name,
                                CASE when pt.uom_id = m.product_uom 
                                THEN coalesce(sum(m.product_qty)::decimal, 0.0)
                                ELSE coalesce(sum(m.product_qty * pu.factor / u.factor )::decimal, 0.0) 
                                END  AS qty
                            FROM product_product pp 
                            LEFT JOIN stock_move m ON (m.product_id=pp.id)
                            LEFT JOIN product_template pt ON (pp.product_tmpl_id=pt.id)
                            LEFT JOIN stock_location l ON (m.location_dest_id=l.id)    
                            LEFT JOIN stock_picking p ON (m.picking_id=p.id)
                            LEFT JOIN uom_uom pu ON (pt.uom_id=pu.id)
                            LEFT JOIN uom_uom u ON (m.product_uom=u.id)
                            WHERE m.date < %s AND (m.location_dest_id in %s) AND m.state='done' AND pp.active=True AND pp.id = %s
                            GROUP BY  pp.id,pt.uom_id , m.product_uom ,pp.default_code,u.name,m.date
                            ))
                        AS foo
                        GROUP BY id
                    ''', (from_date, tuple(locations), product_data, from_date, tuple(locations), product_data))

        res = self._cr.dictfetchall()
        return res[0].get('qty', 0.00)  if res else 0.00

    def _get_beginning_inventoryy(self, record, product, warehouse, location=None):
        locations = location if location else self.get_location(record, warehouse)
        if isinstance(product, int):
            product_data = product
        else:
            product_data = product.id
        start_date = record.start_date
        from_date = self.convert_withtimezone(start_date)
        self._cr.execute('''
                        SELECT id as product_id,coalesce(sum(qty), 0.0) as qty
                        FROM
                            ((
                            SELECT pp.id, pp.default_code,m.date,
                                CASE when pt.uom_id = m.product_uom 
                                THEN u.name 
                                ELSE (select name from uom_uom where id = pt.uom_id) 
                                END AS name,

                                CASE when pt.uom_id = m.product_uom
                                THEN coalesce(sum(-m.product_qty)::decimal, 0.0)
                                ELSE coalesce(sum(-m.product_qty * pu.factor / u.factor )::decimal, 0.0) 
                                END AS qty

                            FROM product_product pp 
                            LEFT JOIN stock_move m ON (m.product_id=pp.id)
                            LEFT JOIN product_template pt ON (pp.product_tmpl_id=pt.id)
                            LEFT JOIN stock_location l ON (m.location_id=l.id)    
                            LEFT JOIN stock_picking p ON (m.picking_id=p.id)
                            LEFT JOIN uom_uom pu ON (pt.uom_id=pu.id)
                            LEFT JOIN uom_uom u ON (m.product_uom=u.id)
                            WHERE m.date <  %s AND (m.location_id in %s) AND m.state='done' AND pp.active=True AND pp.id = %s
                            GROUP BY  pp.id, pt.uom_id , m.product_uom ,pp.default_code,u.name,m.date
                            ) 
                            UNION ALL
                            (
                            SELECT pp.id, pp.default_code,m.date,
                                CASE when pt.uom_id = m.product_uom 
                                THEN u.name 
                                ELSE (select name from uom_uom where id = pt.uom_id) 
                                END AS name,
                                CASE when pt.uom_id = m.product_uom 
                                THEN coalesce(sum(m.product_qty)::decimal, 0.0)
                                ELSE coalesce(sum(m.product_qty * pu.factor / u.factor )::decimal, 0.0) 
                                END  AS qty
                            FROM product_product pp 
                            LEFT JOIN stock_move m ON (m.product_id=pp.id)
                            LEFT JOIN product_template pt ON (pp.product_tmpl_id=pt.id)
                            LEFT JOIN stock_location l ON (m.location_dest_id=l.id)    
                            LEFT JOIN stock_picking p ON (m.picking_id=p.id)
                            LEFT JOIN uom_uom pu ON (pt.uom_id=pu.id)
                            LEFT JOIN uom_uom u ON (m.product_uom=u.id)
                            WHERE m.date < %s AND (m.location_dest_id in %s) AND m.state='done' AND pp.active=True AND pp.id = %s
                            GROUP BY  pp.id,pt.uom_id , m.product_uom ,pp.default_code,u.name,m.date
                            ))
                        AS foo
                        GROUP BY id
                    ''', (from_date, tuple(locations), product_data, from_date, tuple(locations), product_data))

        res = self._cr.dictfetchall()
        return res[0].get('qty', 0.00)  if res else 0.00



    def get_product_sale_qty(self, record, warehouse, product=None, location=None):
        if not product:
            product = self._get_products(record)
        if isinstance(product, list):
            product_data = tuple(
                product)
        else:
            product_data = tuple(product.ids)

        if product_data:
            locations = location if location else self.get_location(record, warehouse)
            start_date = record.start_date.strftime("%Y-%m-%d")  + ' 00:00:00'
            end_date = record.end_date.strftime("%Y-%m-%d")  + ' 23:59:59'

            self._cr.execute('''
                            SELECT pp.id AS product_id,pt.categ_id,
                                sum((
                                CASE WHEN spt.code in ('outgoing') AND smline.location_id in %s AND sourcel.usage !='inventory' AND destl.usage !='inventory'
                                THEN -(smline.qty_done * pu.factor / pu2.factor)
                                ELSE 0.0 
                                END
                                )) AS product_qty_out,
                                 sum((
                                CASE WHEN spt.code in ('incoming') AND smline.location_dest_id in %s AND sourcel.usage !='inventory' AND destl.usage !='inventory' 
                                THEN (smline.qty_done * pu.factor / pu2.factor) 
                                ELSE 0.0 
                                END
                                )) AS product_qty_in,

                                sum((
                                CASE WHEN (spt.code ='internal') AND smline.location_dest_id in %s AND sourcel.usage !='inventory' AND destl.usage !='inventory' 
                                THEN (smline.qty_done * pu.factor / pu2.factor)  
                                WHEN (spt.code ='internal' OR spt.code is null) AND smline.location_id in %s AND sourcel.usage !='inventory' AND destl.usage !='inventory' 
                                THEN -(smline.qty_done * pu.factor / pu2.factor) 
                                ELSE 0.0 
                                END
                                )) AS product_qty_internal,

                                sum((
                                CASE WHEN sourcel.usage = 'inventory' AND smline.location_dest_id in %s  
                                THEN  (smline.qty_done * pu.factor / pu2.factor)
                                WHEN destl.usage ='inventory' AND smline.location_id in %s 
                                THEN -(smline.qty_done * pu.factor / pu2.factor)
                                ELSE 0.0 
                                END
                                )) AS product_qty_adjustment
                            FROM product_product pp 
                            LEFT JOIN stock_move sm ON (sm.product_id = pp.id and sm.date >= %s and sm.date <= %s and sm.state = 'done' and sm.location_id != sm.location_dest_id)
                            LEFT JOIN stock_move_line smline ON (smline.product_id = pp.id and smline.state = 'done' and smline.location_id != smline.location_dest_id and smline.move_id = sm.id)
                            LEFT JOIN stock_picking sp ON (sm.picking_id=sp.id)
                            LEFT JOIN stock_picking_type spt ON (spt.id=sp.picking_type_id)
                            LEFT JOIN stock_location sourcel ON (smline.location_id=sourcel.id)
                            LEFT JOIN stock_location destl ON (smline.location_dest_id=destl.id)
                            LEFT JOIN product_template pt ON (pp.product_tmpl_id=pt.id)
                            LEFT JOIN uom_uom pu ON (pt.uom_id=pu.id)
                            LEFT JOIN uom_uom pu2 ON (smline.product_uom_id=pu2.id)
                            WHERE pp.id in %s
                            GROUP BY pt.categ_id, pp.id order by pt.categ_id
                            ''', (tuple(locations), tuple(locations), tuple(locations), tuple(locations), tuple(locations), tuple(locations), start_date, end_date, product_data))
            values = self._cr.dictfetchall()
            if record.group_by_categ and not location:
                sort_by_categories = sorted(values, key=itemgetter('categ_id'))
                records_by_categories = dict((k, [v for v in itr]) for k, itr in groupby(sort_by_categories, itemgetter('categ_id')))
                return records_by_categories
            else:
                return values[0]

    # def get_pos_sales_after_discount(self, record, product, warehouse):
    #     start_date = record.start_date.strftime("%Y-%m-%d")  + ' 00:00:00'
    #     end_date = record.end_date.strftime("%Y-%m-%d")  + ' 23:59:59'

    #     self._cr.execute('''
    #         SELECT sum(pol.qty) AS qty_with_pos_discount, sum(pol.price_subtotal_incl) AS total_val_with_pos_discount
    #         FROM pos_order_line pol
    #         JOIN pos_order po ON (pol.order_id=po.id and po.date_order >= %s and po.date_order <= %s)
    #         WHERE pol.product_id=%s
    #         ''', (record.start_date, record.end_date, product.id, warehouse.id))
    #     values = self._cr.dictfetchall()
    #     return values

    def get_pos_sales_after_discount(self, record, product, warehouse):

        start_date = record.start_date.strftime("%Y-%m-%d")  + ' 00:00:00'
        end_date = record.end_date.strftime("%Y-%m-%d")  + ' 23:59:59'

        self._cr.execute('''
            SELECT sum(pol.qty) AS qty_with_pos_discount, sum(pol.price_subtotal_incl) AS total_val_with_pos_discount
            FROM pos_order_line pol
            JOIN pos_order po ON (pol.order_id=po.id and po.date_order >= %s and po.date_order <= %s)
            JOIN pos_session session ON po.session_id=session.id
            JOIN pos_config config ON config.id=session.config_id
            JOIN stock_picking_type spt ON (spt.id=config.picking_type_id and spt.warehouse_id=%s)
            WHERE pol.product_id=%s
            ''', (record.start_date, record.end_date, warehouse.id, product.id))
        values = self._cr.dictfetchall()
        return values

    def get_total_sales_after_discount(self, record, product, warehouse):
        self._cr.execute('''
            SELECT sum(sol.product_uom_qty) AS qty_with_sales_discount, sum(sol.price_total) AS total_val_with_sales_discount
            FROM sale_order_line sol
            JOIN sale_order so ON (sol.order_id=so.id and so.date_order >= %s and so.date_order <= %s and so.warehouse_id=%s)
            WHERE sol.product_id=%s
            ''', (record.start_date, record.end_date, warehouse.id, product.id))
        values = self._cr.dictfetchall()
        return values

    def get_online_sales_after_discount(self, record, product, warehouse):
        self._cr.execute('''
            SELECT sum(sol.product_uom_qty) AS qty_with_sales_discount, sum(sol.price_total) AS total_val_with_sales_discount
            FROM sale_order_line sol
            JOIN sale_order so ON (sol.order_id=so.id and so.date_order >= %s and so.date_order <= %s and so.warehouse_id=%s)
            WHERE sol.product_id=%s and so.website_id is not null
            ''', (record.start_date, record.end_date, warehouse.id, product.id))
        values = self._cr.dictfetchall()
        return values

    def get_product_sale_qtyy(self, record, warehouse, product=None, location=None):
        if not product:
            product = self._get_products(record)
        if isinstance(product, list):
            product_data = tuple(product)
        else:
            product_data = tuple(product.ids)
        if product_data:
            locations = location if location else self.get_locationn(record, warehouse)
            start_date = record.start_date.strftime("%Y-%m-%d")  + ' 00:00:00'
            end_date = record.end_date.strftime("%Y-%m-%d")  + ' 23:59:59'

            self._cr.execute('''
                            SELECT pp.id AS product_id,pt.categ_id,
                                %s as warehouse_id,
                                sum((
                                CASE WHEN spt.code in ('outgoing') AND smline.location_id in %s AND sourcel.usage not in ('inventory', 'supplier') AND destl.usage not in ('inventory', 'supplier')
                                THEN -(smline.qty_done * pu.factor / pu2.factor)
                                ELSE 0.0 
                                END
                                )) AS product_qty_out,

                                 sum((
                                CASE WHEN spt.code in ('incoming') AND smline.location_dest_id in %s AND sourcel.usage !='inventory' AND destl.usage !='inventory' 
                                THEN (smline.qty_done * pu.factor / pu2.factor) 
                                ELSE 0.0 
                                END
                                )) AS product_qty_in,

                                sum((
                                CASE WHEN (spt.code ='internal') AND smline.location_dest_id in %s AND sourcel.usage !='inventory' AND destl.usage !='inventory'
                                THEN (smline.qty_done * pu.factor / pu2.factor)  
                                WHEN (spt.code ='internal' OR spt.code is null) AND smline.location_id in %s AND sourcel.usage !='inventory' AND destl.usage !='inventory'
                                THEN -(smline.qty_done * pu.factor / pu2.factor) 
                                ELSE 0.0 
                                END
                                )) AS product_qty_internal,

                                sum((
                                CASE WHEN sourcel.usage = 'inventory' AND smline.location_dest_id in %s  
                                THEN  (smline.qty_done * pu.factor / pu2.factor)
                                WHEN destl.usage ='inventory' AND smline.location_id in %s 
                                THEN -(smline.qty_done * pu.factor / pu2.factor)
                                ELSE 0.0 
                                END
                                )) AS product_qty_adjustment,

                                sum((
                                    CASE WHEN destl.usage = 'supplier' THEN (smline.qty_done)
                                    ELSE 0
                                    END
                                    )) AS product_rtn_qty

                            FROM product_product pp 
                            LEFT JOIN stock_move sm ON (sm.product_id = pp.id and sm.date >= %s and sm.date <= %s and sm.state = 'done' and sm.location_id != sm.location_dest_id)
                            LEFT JOIN stock_move_line smline ON (smline.product_id = pp.id and smline.state = 'done' and smline.location_id != smline.location_dest_id and smline.move_id = sm.id)
                            LEFT JOIN stock_picking sp ON (sm.picking_id=sp.id)
                            LEFT JOIN stock_picking_type spt ON (spt.id=sp.picking_type_id)
                            LEFT JOIN stock_location sourcel ON (smline.location_id=sourcel.id)
                            LEFT JOIN stock_location destl ON (smline.location_dest_id=destl.id)
                            LEFT JOIN product_template pt ON (pp.product_tmpl_id=pt.id)
                            LEFT JOIN uom_uom pu ON (pt.uom_id=pu.id)
                            LEFT JOIN uom_uom pu2 ON (smline.product_uom_id=pu2.id)
                            WHERE pp.id in %s
                            GROUP BY pt.categ_id, pp.id order by pt.categ_id
                            ''', (warehouse.id, tuple(locations), tuple(locations), tuple(locations), tuple(locations), tuple(locations), tuple(locations), start_date, end_date, product_data))
            
            values = self._cr.dictfetchall()
            info = {}
            if True:
                sort_by_categories = sorted(values, key=itemgetter('categ_id'))
                sort_by_warehouses = sorted(values, key=itemgetter('warehouse_id'))
                records_by_categories = dict((k, [v for v in itr]) for k, itr in groupby(sort_by_categories, itemgetter('categ_id')))
                records_by_warehouses = dict((k, [v for v in itr]) for k, itr in groupby(sort_by_warehouses, itemgetter('warehouse_id')))
                
                for warehouse_id in records_by_warehouses:
                    sort_by_warehouses = sorted(records_by_warehouses.get(warehouse_id), key=itemgetter('categ_id'))
                    records_by_warehouses_1 = dict((k, [v for v in itr]) for k, itr in groupby(sort_by_warehouses, itemgetter('categ_id')))
                    warehouse = self.env['stock.warehouse'].browse(warehouse_id)
                    info[warehouse] = records_by_warehouses_1
                # days = (record.end_date - record.start_date) + timedelta(days=1)
                days = (record.end_date - record.start_date + timedelta(days=1)).days
                for warehouse in info:
                    categories = info.get(warehouse)
                    sum_begning_value_warehouse = sum_beginning_qty_warehouse = 0
                    sum_categ_product_qty_in_value_warehouse = sum_categ_product_qty_in_warehouse = 0
                    purchase_rtn_val_warehouse = purchase_rtn_qty_warehouse = 0
                    promotion_claim_val_warehouse = promotion_claim_qty_warehouse = 0
                    in_kind_stock_val_warehouse = in_kind_stock_qty_warehouse = 0
                    sum_categ_product_qty_internal_value_warehouse = sum_categ_product_qty_internal_warehouse = 0
                    sum_categ_product_qty_adjustment_value_warehouse = sum_categ_product_qty_adjustment_warehouse = 0
                    total_stock_value_warehouse = total_stock_qty_warehouse = 0
                    total_cogs_val_warehouse = total_cogs_qty_warehouse = 0
                    pos_sales_after_discount_val_warehouse = pos_sales_after_discount_qty_warehouse = 0
                    credit_sales_val_warehouse = credit_sales_qty_warehouse = 0
                    online_sales_val_warehouse = online_sales_qty_warehouse = 0
                    total_sales_amount_after_discount_warehouse = total_sale_qty_after_discount_warehouse = 0
                    gross_profit_before_shrinkage_warehouse = gross_profit_before_shrinkage_percent_warehouse = 0
                    disposal_val_warehouse = disposal_percent_warehouse = 0
                    unknown_shrinkage_val_warehouse = unknown_shrinkage_val_percent_warehouse = 0
                    gross_profit_after_discount_shrinkage_val_warehouse = gross_profit_after_discount_shrinkage_percent_warehouse = 0
                    inv_day_on_hand_warehouse = inv_day_on_hand_percent_warehouse = 0
                    for category in categories:
                        sum_begning_value_categ = sum_beginning_qty_categ = 0
                        sum_categ_product_qty_in_value_categ = sum_categ_product_qty_in_categ = 0
                        purchase_rtn_val_categ = purchase_rtn_qty_categ = 0
                        promotion_claim_val_categ = promotion_claim_qty_categ = 0
                        in_kind_stock_val_categ = in_kind_stock_qty_categ = 0
                        sum_categ_product_qty_internal_value_categ = sum_categ_product_qty_internal_categ = 0
                        sum_categ_product_qty_adjustment_value_categ = sum_categ_product_qty_adjustment_categ = 0
                        total_stock_value_categ = total_stock_qty_categ = 0
                        total_cogs_val_categ = total_cogs_percent_categ = 0
                        pos_sales_after_discount_val_categ = pos_sales_after_discount_qty_categ = 0
                        credit_sales_val_categ = credit_sales_qty_categ = 0
                        online_sales_val_categ = online_sales_qty_categ = 0
                        total_sales_amount_after_discount_categ = total_sale_qty_after_discount_categ = 0
                        gross_profit_before_shrinkage_categ = gross_profit_before_shrinkage_percent_categ = 0
                        disposal_val_categ = disposal_percent_categ = 0
                        unknown_shrinkage_val_categ = unknown_shrinkage_val_percent_categ = 0
                        gross_profit_after_discount_shrinkage_val_categ = gross_profit_after_discount_shrinkage_percent_categ = 0
                        inv_day_on_hand_categ = inv_day_on_hand_percent_categ = 0
                        for product_data in categories.get(category):
                            product = self.env['product.product'].browse(product_data.get('product_id'))
                            get_beginning_inventory = self._get_beginning_inventoryy(record, product_data.get('product_id'), warehouse) if warehouse else 0

                            # sum_begning_value = self.get_product_valuation(record, product, get_beginning_inventory, warehouse, 'beg') if warehouse else 0
                            sum_begning_value = round(get_beginning_inventory * product.standard_price, 2)

                            sum_categ_product_qty_in_value = self.get_product_valuation(record, product, product_data.get('product_qty_in'), warehouse, 'in') if warehouse else 0
                                
                            sum_categ_product_qty_out_value = abs(self.get_product_valuation(record, product, product_data.get('product_qty_out'), warehouse, 'out')) if warehouse else 0

                            sum_categ_product_qty_internal_value = self.get_product_valuation(record, product, product_data.get('product_qty_internal'), warehouse, 'int') if warehouse else 0
                            sum_categ_product_qty_adjustment_value = round(self.get_product_valuation(record, product, product_data.get('product_qty_adjustment'), warehouse, 'adj'), 2) if warehouse else 0

                            purchase_rtn_val = self.get_product_valuation(record, product, product_data.get('product_rtn_qty'), warehouse, 'purchase_return') if warehouse else 0
                            purchase_rtn_qty = product_data.get('product_rtn_qty')
                            
                            promotion_claim_val = 0
                            promotion_claim_qty = 0

                            in_kind_stock_val = 0
                            in_kind_stock_qty = 0

                            pos_data = self.get_pos_sales_after_discount(record, product, warehouse)[0]

                            pos_sales_after_discount_val = pos_data.get('total_val_with_pos_discount') or 0
                            pos_sales_after_discount_qty = pos_data.get('qty_with_pos_discount') or 0
                            
                            sales_data = self.get_total_sales_after_discount(record, product, warehouse)[0]
                            credit_sales_val = sales_data.get('total_val_with_sales_discount') or 0
                            credit_sales_qty = sales_data.get('qty_with_sales_discount') or 0

                            online_sales_data = self.get_online_sales_after_discount(record, product, warehouse)[0]
                            online_sales_val = online_sales_data.get('total_val_with_sales_discount') or 0
                            online_sales_qty = online_sales_data.get('qty_with_sales_discount') or 0

                            total_sales_amount_after_discount = round(pos_sales_after_discount_val + credit_sales_val + online_sales_val, 2)
                            total_sale_qty_after_discount = round(pos_sales_after_discount_qty + credit_sales_qty + online_sales_qty, 2)
                            
                            gross_profit_before_shrinkage = 0
                            gross_profit_before_shrinkage_percent = round((gross_profit_before_shrinkage / total_sale_qty_after_discount) * 100, 2) if total_sale_qty_after_discount else 0
                            # stock_value = round(sum_begning_value + sum_categ_product_qty_in_value + purchase_rtn_val + promotion_claim_val + in_kind_stock_val + sum_categ_product_qty_internal_value + sum_categ_product_qty_adjustment_value, 2)
                            stock_value = round(sum_begning_value + sum_categ_product_qty_in_value + sum_categ_product_qty_internal_value + sum_categ_product_qty_adjustment_value, 2)
                            
                            # total_stock_value = round(stock_value - total_sales_amount_after_discount - gross_profit_before_shrinkage, 2)
                            gross_profit_after_discount_shrinkage_val = round(total_sales_amount_after_discount - sum_categ_product_qty_out_value, 2)
                            total_stock_value = round(stock_value - total_sales_amount_after_discount + gross_profit_after_discount_shrinkage_val, 2)

                            # total_stock_qty = round(get_beginning_inventory + product_data.get('product_qty_in') + purchase_rtn_qty + in_kind_stock_qty + product_data.get('product_qty_adjustment') + product_data.get('product_qty_internal') - total_sale_qty_after_discount, 2)
                            total_stock_qty = round(get_beginning_inventory + product_data.get('product_qty_in') + product_data.get('product_qty_adjustment') + product_data.get('product_qty_internal') - total_sale_qty_after_discount, 2)
                            #total_stock_qty = round(total_sale_qty_after_discount / total_stock_qty, 2) if total_stock_qty else 0
                            total_cogs_val = round(sum_categ_product_qty_out_value / total_stock_value, 2) if total_stock_value else 0
                            toal_cogs_percent = round(total_cogs_val / total_stock_value, 2) * 100 if total_stock_value else 0

                            disposal_val = 0
                            disposal_percent = round((disposal_val / total_sales_amount_after_discount) * 100, 2) if total_sales_amount_after_discount else 0

                            unknown_shrinkage_val = 0
                            unknown_shrinkage_val_percent = round((unknown_shrinkage_val / total_sales_amount_after_discount) * 100, 2) if total_sales_amount_after_discount else 0
                             
                            inv_day_on_hand = round(total_stock_value / total_sales_amount_after_discount, 2) if total_sales_amount_after_discount else 0

                            inv_day_on_hand_percent = 0
                            if (total_sale_qty_after_discount / days):
                                inv_day_on_hand_percent = round(total_stock_qty / (total_sale_qty_after_discount / days), 2)
                            
                            # if gross_profit_before_shrinkage - disposal_val:
                            #     inv_day_on_hand_percent = round((unknown_shrinkage_val / (gross_profit_before_shrinkage - disposal_val)) * 100, 2)

                            # total_sales_value = sum_begning_value + sum_categ_product_qty_in_value + purchase_rtn_val + promotion_claim_val + in_kind_stock_val + sum_categ_product_qty_internal_value + sum_categ_product_qty_adjustment_value

                            product_data.update({'product_beg_qty': get_beginning_inventory, 
                                'sum_begning_value': sum_begning_value,
                                'sum_categ_product_qty_in_value': sum_categ_product_qty_in_value,    
                                'purchase_rtn_val': purchase_rtn_val,
                                'purchase_rtn_qty': purchase_rtn_qty,
                                'promotion_claim_val': promotion_claim_val, 
                                'promotion_claim_qty': promotion_claim_qty, 
                                'in_kind_stock_val': in_kind_stock_val,
                                'in_kind_stock_qty': in_kind_stock_qty,
                                'sum_categ_product_qty_internal_value': sum_categ_product_qty_internal_value,
                                'sum_categ_product_qty_adjustment_value': sum_categ_product_qty_adjustment_value,
                                'total_stock_value': total_stock_value,
                                'total_stock_qty': total_stock_qty,
                                'total_sales_value': 0,
                                'total_sales_value_percent': 0,
                                'total_cogs_val': total_cogs_val,
                                'toal_cogs_percent': toal_cogs_percent,
                                'pos_sales_after_discount_val': pos_sales_after_discount_val,
                                'pos_sales_after_discount_qty': pos_sales_after_discount_qty,
                                'credit_sales_val': credit_sales_val,
                                'credit_sales_qty': credit_sales_qty,
                                'online_sales_val': online_sales_val, 
                                'online_sales_qty': online_sales_qty, 
                                'total_sales_amount_after_discount': total_sales_amount_after_discount, 
                                'total_sale_qty_after_discount': total_sale_qty_after_discount,
                                'gross_profit_before_shrinkage': gross_profit_before_shrinkage, 
                                'gross_profit_before_shrinkage_percent': gross_profit_before_shrinkage_percent, 
                                'disposal_val': disposal_val, 
                                'disposal_percent': disposal_percent,
                                'unknown_shrinkage_val': unknown_shrinkage_val,
                                'unknown_shrinkage_val_percent': unknown_shrinkage_val_percent,
                                'gross_profit_after_discount_shrinkage_val': gross_profit_after_discount_shrinkage_val,
                                # 'gross_profit_after_discount_shrinkage_percent': round((gross_profit_before_shrinkage / total_sales_amount_after_discount) * 100, 2) if total_sales_amount_after_discount else 0,
                                'gross_profit_after_discount_shrinkage_percent': round((gross_profit_after_discount_shrinkage_val / total_sales_amount_after_discount) * 100, 2) if total_sales_amount_after_discount else 0,
                                'inv_day_on_hand': inv_day_on_hand,
                                'inv_day_on_hand_percent': inv_day_on_hand_percent
                                })
                            
                            sum_begning_value_categ += sum_begning_value
                            sum_beginning_qty_categ += get_beginning_inventory
                            sum_categ_product_qty_in_value_categ += sum_categ_product_qty_in_value
                            sum_categ_product_qty_in_categ += product_data.get('product_qty_in')
                            

                            purchase_rtn_val_categ += purchase_rtn_val
                            promotion_claim_val_categ += promotion_claim_val

                            in_kind_stock_val_categ += in_kind_stock_val
                            sum_categ_product_qty_internal_value_categ += sum_categ_product_qty_internal_value
                            sum_categ_product_qty_internal_categ += product_data.get('product_qty_internal')

                            sum_categ_product_qty_adjustment_value_categ += sum_categ_product_qty_adjustment_value
                            sum_categ_product_qty_adjustment_categ += product_data.get('product_qty_adjustment')

                            total_stock_value_categ += total_stock_value
                            total_stock_qty_categ += total_stock_qty
                            
                            total_cogs_val_categ += total_cogs_val
                            # total_cogs_percent_categ += toal_cogs_percent
                            
                            pos_sales_after_discount_val_categ += pos_sales_after_discount_val
                            pos_sales_after_discount_qty_categ += pos_sales_after_discount_qty
                            credit_sales_val_categ += credit_sales_val
                            credit_sales_qty_categ += credit_sales_qty
                            online_sales_val_categ += online_sales_val
                            online_sales_qty_categ += online_sales_qty
                            total_sales_amount_after_discount_categ += total_sales_amount_after_discount
                            total_sale_qty_after_discount_categ += total_sale_qty_after_discount

                            gross_profit_before_shrinkage_categ += gross_profit_before_shrinkage
                            # gross_profit_before_shrinkage_percent_categ += gross_profit_before_shrinkage_percent

                            disposal_val_categ += disposal_val
                            # disposal_percent_categ += disposal_percent

                            unknown_shrinkage_val_categ += unknown_shrinkage_val
                            # unknown_shrinkage_val_percent_categ += unknown_shrinkage_val_percent

                            gross_profit_after_discount_shrinkage_val_categ += gross_profit_after_discount_shrinkage_val
                            # gross_profit_after_discount_shrinkage_percent_categ += gross_profit_after_discount_shrinkage_percent_categ
#                            gross_profit_after_discount_shrinkage_percent_categ = (gross_profit_after_discount_shrinkage_val_categ / total_sales_amount_after_discount_categ) * 100 if total_sales_amount_after_discount_categ else 0

                            inv_day_on_hand_categ += inv_day_on_hand
                            inv_day_on_hand_percent_categ = inv_day_on_hand_percent


                        # inv_day_on_hand_percent_categ = 0
                        # if gross_profit_before_shrinkage_categ - disposal_val_categ:
                        #     inv_day_on_hand_percent = round((unknown_shrinkage_val_categ / (gross_profit_before_shrinkage_categ - disposal_val_categ)) * 100, 2)

                        inv_day_on_hand_percent_categ = 0
                        if (total_sale_qty_after_discount_categ / days):
                            inv_day_on_hand_percent_categ = round(total_stock_qty_categ / (total_sale_qty_after_discount_categ / days), 2)

                        categories.get(category).append({'sum_begning_value_categ': sum_begning_value_categ,
                            'sum_beginning_qty_categ': sum_beginning_qty_categ,
                            'sum_categ_product_qty_in_value_categ': sum_categ_product_qty_in_value_categ,
                            'sum_categ_product_qty_in_categ': sum_categ_product_qty_in_categ,
                            'purchase_rtn_val_categ': purchase_rtn_val_categ,
                            'promotion_claim_val_categ': promotion_claim_val_categ,
                            'in_kind_stock_val_categ': in_kind_stock_val_categ,
                            'sum_categ_product_qty_internal_value_categ': sum_categ_product_qty_internal_value_categ,
                            'sum_categ_product_qty_internal_categ': sum_categ_product_qty_internal_categ,
                            'sum_categ_product_qty_adjustment_value': sum_categ_product_qty_adjustment_value_categ,
                            'sum_categ_product_qty_adjustment_categ': sum_categ_product_qty_adjustment_categ,
                            'total_stock_value_categ': total_stock_value_categ,
                            'total_stock_qty_categ': total_stock_qty_categ,
                            'total_cogs_val_categ': total_cogs_val_categ,
                            'total_cogs_percent_categ': round(total_cogs_val_categ / total_stock_value_categ, 2) if total_stock_value_categ else 0,
                            'pos_sales_after_discount_val_categ': pos_sales_after_discount_val_categ,
                            'pos_sales_after_discount_qty_categ': pos_sales_after_discount_qty_categ,
                            'credit_sales_val_categ': credit_sales_val_categ,
                            'credit_sales_qty_categ': credit_sales_qty_categ,
                            'online_sales_val_categ': online_sales_val_categ,
                            'online_sales_qty_categ': online_sales_qty_categ,
                            'total_sales_amount_after_discount_categ': total_sales_amount_after_discount_categ,
                            'total_sale_qty_after_discount_categ': total_sale_qty_after_discount_categ,
                            'gross_profit_before_shrinkage_categ': gross_profit_before_shrinkage_categ,
                            'gross_profit_before_shrinkage_percent_categ': round(gross_profit_before_shrinkage_categ / total_sales_amount_after_discount_categ, 2) if total_sales_amount_after_discount_categ else 0,
                            'disposal_val_categ': disposal_val_categ,
                            'disposal_percent_categ': round(disposal_val_categ / total_sales_amount_after_discount_categ, 2) if total_sales_amount_after_discount_categ else 0,
                            'unknown_shrinkage_val_categ': unknown_shrinkage_val_categ,
                            'unknown_shrinkage_val_percent_categ': round((unknown_shrinkage_val_percent_categ / total_sales_amount_after_discount_categ) * 100, 2) if total_sales_amount_after_discount_categ else 0,
                            'gross_profit_after_discount_shrinkage_val_categ': gross_profit_after_discount_shrinkage_val_categ,
                            # 'gross_profit_after_discount_shrinkage_percent_categ': round((gross_profit_before_shrinkage_categ / total_sales_amount_after_discount_categ) * 100, 2) if total_sales_amount_after_discount_categ else 0,
                            'gross_profit_after_discount_shrinkage_percent_categ': round((gross_profit_after_discount_shrinkage_val_categ / total_sales_amount_after_discount_categ) * 100, 2) if total_sales_amount_after_discount_categ else 0,
                            'inv_day_on_hand_categ': inv_day_on_hand_categ,
                            'inv_day_on_hand_percent_categ': inv_day_on_hand_percent_categ
                            })

                        sum_begning_value_warehouse += sum_begning_value_categ
                        sum_beginning_qty_warehouse += sum_beginning_qty_warehouse                          
                        
                        sum_categ_product_qty_in_value_warehouse += sum_categ_product_qty_in_value_categ
                        sum_categ_product_qty_in_warehouse += sum_categ_product_qty_in_categ
                        
                        purchase_rtn_val_warehouse += purchase_rtn_val_categ
                        promotion_claim_val_warehouse += promotion_claim_val_categ 
                        in_kind_stock_val_warehouse += in_kind_stock_val_categ

                        sum_categ_product_qty_internal_value_warehouse += sum_categ_product_qty_internal_value_categ
                        sum_categ_product_qty_internal_warehouse += sum_categ_product_qty_internal_categ
                        
                        sum_categ_product_qty_adjustment_value_warehouse += sum_categ_product_qty_adjustment_value_categ
                        sum_categ_product_qty_adjustment_warehouse += sum_categ_product_qty_adjustment_categ

                        total_stock_value_warehouse += total_stock_value_categ
                        total_stock_qty_warehouse += total_stock_qty_categ
                        
                        total_cogs_val_warehouse += total_cogs_val_categ
                        # total_cogs_percent_categ += toal_cogs_percent
                        
                        pos_sales_after_discount_val_warehouse += pos_sales_after_discount_val_categ
                        pos_sales_after_discount_qty_warehouse += pos_sales_after_discount_qty_categ
                        credit_sales_val_warehouse += credit_sales_val_categ 
                        credit_sales_qty_warehouse += credit_sales_qty_categ 
                        online_sales_val_warehouse += online_sales_val_categ 
                        online_sales_qty_warehouse += online_sales_qty_categ 
                        total_sales_amount_after_discount_warehouse += total_sales_amount_after_discount_categ
                        total_sale_qty_after_discount_warehouse += total_sale_qty_after_discount_categ

                        gross_profit_before_shrinkage_warehouse += gross_profit_before_shrinkage_categ
                        # gross_profit_before_shrinkage_percent_warehouse += gross_profit_before_shrinkage_percent_categ

                        disposal_val_warehouse += disposal_val_categ
                        # disposal_percent_warehouse += disposal_percent_categ

                        unknown_shrinkage_val_warehouse += unknown_shrinkage_val_categ
                        # unknown_shrinkage_val_percent_categ += unknown_shrinkage_val_percent

                        gross_profit_after_discount_shrinkage_val_warehouse += gross_profit_after_discount_shrinkage_val_categ
                        # gross_profit_after_discount_shrinkage_percent_categ += gross_profit_after_discount_shrinkage_percent_categ

                        inv_day_on_hand_warehouse += inv_day_on_hand_categ
                        # inv_day_on_hand_percent_warehouse += inv_day_on_hand_percent_categ

                    # inv_day_on_hand_percent_warehouse = 0
                    # if gross_profit_before_shrinkage_warehouse - disposal_val_warehouse:
                    #     inv_day_on_hand_percent_warehouse = round((unknown_shrinkage_val_warehouse / (gross_profit_before_shrinkage_warehouse - disposal_val_warehouse)) * 100, 2)

                    inv_day_on_hand_percent_warehouse = 0
                    if (total_sale_qty_after_discount_warehouse / days):
                        inv_day_on_hand_percent_warehouse = round(total_stock_qty_warehouse / (total_sale_qty_after_discount_warehouse / days), 2)

                    info.get(warehouse)['warehouse_data'] = {'sum_begning_value_warehouse': sum_begning_value_warehouse,
                    'sum_beginning_qty_warehouse': sum_beginning_qty_warehouse,
                    'sum_categ_product_qty_in_value_warehouse': sum_categ_product_qty_in_value_warehouse,
                    'sum_categ_product_qty_in_warehouse': sum_categ_product_qty_in_warehouse,
                    'sum_categ_product_qty_in_value_warehouse': sum_categ_product_qty_in_value_warehouse,
                    'purchase_rtn_val_warehouse': purchase_rtn_val_warehouse,
                    'promotion_claim_val_warehouse': promotion_claim_val_warehouse,
                    'in_kind_stock_val_warehouse': in_kind_stock_val_warehouse,
                    'sum_categ_product_qty_internal_value_warehouse': sum_categ_product_qty_internal_value_warehouse,
                    'sum_categ_product_qty_internal_warehouse': sum_categ_product_qty_internal_warehouse,
                    'sum_categ_product_qty_adjustment_value': sum_categ_product_qty_adjustment_value_warehouse,
                    'sum_categ_product_qty_adjustment_warehouse': sum_categ_product_qty_adjustment_warehouse,
                    'total_stock_value_warehouse': total_stock_value_warehouse,
                    'total_stock_qty_warehouse': total_stock_qty_warehouse,
                    'total_cogs_val_warehouse': total_cogs_val_warehouse,
                    'total_cogs_percent_warehouse': round(total_cogs_val_warehouse / total_stock_value_warehouse, 2) if total_stock_value_warehouse else 0,
                    'pos_sales_after_discount_val_warehouse': pos_sales_after_discount_val_warehouse,
                    'pos_sales_after_discount_qty_warehouse': pos_sales_after_discount_qty_warehouse,
                    'credit_sales_val_warehouse': credit_sales_val_warehouse,
                    'credit_sales_qty_warehouse': credit_sales_qty_warehouse,
                    'online_sales_val_warehouse': online_sales_val_warehouse,
                    'online_sales_qty_warehouse': online_sales_qty_warehouse,
                    'total_sales_amount_after_discount_warehouse': total_sales_amount_after_discount_warehouse,
                    'total_sale_qty_after_discount_warehouse': total_sale_qty_after_discount_warehouse,
                    'gross_profit_before_shrinkage_warehouse': gross_profit_before_shrinkage_warehouse,
                    'gross_profit_before_shrinkage_percent_warehouse': round(gross_profit_before_shrinkage_warehouse / total_sales_amount_after_discount_warehouse, 2) if total_sales_amount_after_discount_warehouse else 0,
                    'disposal_val_warehouse': disposal_val_warehouse,
                    'disposal_percent_warehouse': round(disposal_val_warehouse / total_sales_amount_after_discount_warehouse, 2) if total_sales_amount_after_discount_warehouse else 0,
                    'unknown_shrinkage_val_warehouse': unknown_shrinkage_val_warehouse,
                    'unknown_shrinkage_val_percent_warehouse': round(unknown_shrinkage_val_percent_warehouse / total_sales_amount_after_discount_warehouse, 2) if total_sales_amount_after_discount_warehouse else 0,
                    'gross_profit_after_discount_shrinkage_val_warehouse': gross_profit_after_discount_shrinkage_val_warehouse,
                    # 'gross_profit_after_discount_shrinkage_percent_warehouse': round(gross_profit_before_shrinkage_warehouse / total_sales_amount_after_discount_warehouse, 2) if total_sales_amount_after_discount_warehouse else 0,
                    'gross_profit_after_discount_shrinkage_percent_warehouse': round((gross_profit_after_discount_shrinkage_val_warehouse / total_sales_amount_after_discount_warehouse) * 100, 2) if total_sales_amount_after_discount_warehouse else 0,
                    'inv_day_on_hand_warehouse': inv_day_on_hand_warehouse,
                    'inv_day_on_hand_percent_warehouse': inv_day_on_hand_percent_warehouse
                    }
                return info
            else:
                pass
                # return values[0]

    def get_product_valuation(self, record, product_id, quantity, warehouse, op_type):
        value = 0.00
        location_ids = self.get_warehouse_wise_location(record,warehouse).ids
        value = self._get_stock_move_valuation(record,product_id,warehouse,op_type,location_ids,quantity)
        return round(value, 2)

    def _get_stock_move_valuation(self, record, product, warehouse, op_type, location_ids,quantity):
        product_price = self.env['decimal.precision'].precision_get('Product Price')
        StockMove = self.env['stock.move']
        end_date = record.end_date.strftime("%Y-%m-%d")  + ' 23:59:59'
        domain = [('product_id','=',product.id),('company_id','=',record.company_id.id)]

        value = 0.00
        if op_type == 'purchase_return':
            domain += [('create_date', '>=', record.start_date),('create_date', '<=', end_date),
            ('stock_move_id.picking_code','=','outgoing'), ('stock_move_id.location_dest_id.usage','=','supplier')]
        if op_type == 'beg':
            domain.append(('create_date', '<', record.start_date))
        if op_type == 'in':
            domain += [('create_date', '>=', record.start_date),('create_date', '<=', end_date),
                '|',('stock_move_id','=',False),('stock_move_id.picking_code','=','incoming')]
        if op_type == 'out':
            domain += [('create_date', '>=', record.start_date),('create_date', '<=', end_date),
                '|',('stock_move_id','=',False),('stock_move_id.picking_code','=','outgoing')]
        if op_type == 'adj':
            domain += [('create_date', '>=', record.start_date),('create_date', '<=', end_date),
                '|',('stock_move_id','=',False),('stock_move_id.inventory_id','!=',False)]
        valuation_layer_ids = self.env['stock.valuation.layer'].search(domain)
        value = sum(valuation_layer_ids.mapped('value'))
        if op_type in ['int','final']:
            value = quantity * product.standard_price
        if not quantity:
            value =  0
        return float_round(value,precision_digits=product_price)
        # return float_round(value,precision_digits=2)



# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:
