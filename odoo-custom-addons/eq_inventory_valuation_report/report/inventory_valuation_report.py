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
from datetime import datetime, date


class eq_inventory_valuation_report_inventory_valuation_report(models.AbstractModel):
    _name = 'report.eq_inventory_valuation_report.inventory_valuation_report'

    @api.model
    def _get_report_values(self, docids, data=None):
        report = self.env['ir.actions.report']._get_report_from_name('eq_inventory_valuation_report.inventory_valuation_report')
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
           'get_product_valuation':self.get_product_valuation

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
        if record.category_ids:
            domain.append(('categ_id', 'in', record.category_ids.ids))
            product_ids = product_product_obj.search(domain)
        if record.product_ids:
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

    def get_product_sale_qty(self, record, warehouse, product=None, location=None):
        if not product:
            product = self._get_products(record)
        if isinstance(product, list):
            product_data = tuple(product)
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

    def get_product_valuation(self,record,product_id,quantity,warehouse,op_type):
        value = 0.00
        location_ids = self.get_warehouse_wise_location(record,warehouse).ids
        value = self._get_stock_move_valuation(record,product_id,warehouse,op_type,location_ids,quantity)
        return value

    def _get_stock_move_valuation(self, record, product, warehouse, op_type, location_ids,quantity):
        product_price = self.env['decimal.precision'].precision_get('Product Price')
        StockMove = self.env['stock.move']
        end_date = record.end_date.strftime("%Y-%m-%d")  + ' 23:59:59'
        domain = [('product_id','=',product.id),('company_id','=',record.company_id.id)]

        value = 0.00
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


# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4: