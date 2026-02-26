# -*- coding: utf-8 -*-
# Part of BrowseInfo. See LICENSE file for full copyright and licensing details.

from odoo import models, api, _
import operator

class LowSalesReportTemplate(models.AbstractModel):
    _name = 'report.bi_low_sales_report.report_low_sales'
    _description = 'Low Sales Report Template'


    def _get_product_detail(self, data):
        date_from = data.get('date_from')
        date_to = data.get('date_to')
        quantity = data.get('quantity')
        amount = data.get('amount')
        report_type = data.get('report_type')
        product_category_ids = data.get('product_category_ids')
        product_template_ids = self.env['product.template'].search([])
        product_ids = self.env['product.product'].search([])

        order_line_lst = []
        if report_type == 'product':
            for product in product_template_ids:
                order_line_ids = self.env['sale.order.line'].search([('order_id.date_order','>=',date_from),('order_id.date_order','<=',date_to),('product_id.product_tmpl_id','in',product.ids)])
                product_qty_sum = sum([line.product_uom_qty for line in order_line_ids])
                price_unit_sum = sum([line.price_unit for line in order_line_ids])
                revenu_total = product_qty_sum * price_unit_sum
                order_line_lst.append({'product': product, 'quantity': product_qty_sum, 'total_revenue': revenu_total,'price_unit': price_unit_sum})
        
        elif report_type == 'product_variant':
            for product in product_ids:
                order_line_ids = self.env['sale.order.line'].search([('order_id.date_order','>=',date_from),('order_id.date_order','<=',date_to),('product_id','in',product.ids)])
                product_qty_sum = sum([line.product_uom_qty for line in order_line_ids])
                price_unit_sum = sum([line.price_unit for line in order_line_ids])
                revenu_total = product_qty_sum * price_unit_sum
                order_line_lst.append({'product': product, 'quantity': product_qty_sum, 'total_revenue': revenu_total, 'price_unit': price_unit_sum, })

        elif report_type == 'product_category':
            if product_category_ids:
                for product in product_ids.filtered(lambda a: a.categ_id.id in product_category_ids.ids):
                    order_line_ids = self.env['sale.order.line'].search([('order_id.date_order','>=',date_from),('order_id.date_order','<=',date_to),('product_id','in',product.ids)])
                    product_qty_sum = sum([line.product_uom_qty for line in order_line_ids])
                    price_unit_sum = sum([line.price_unit for line in order_line_ids])
                    revenu_total = product_qty_sum * price_unit_sum
                    order_line_lst.append({'product': product, 'quantity': product_qty_sum, 'total_revenue': revenu_total,'price_unit': price_unit_sum})

        return order_line_lst

    @api.model
    def _get_report_values(self, docids, data=None):
        report_type = data['form']['report_type']
        date_from = data['form']['date_from']
        date_to = data['form']['date_to']
        quantity = data['form']['quantity']
        amount = data['form']['amount']
        product_category_ids = self.env['product.category'].browse(data['form']['product_category_ids'])
        data  = { 
            'report_type'   : report_type,
            'date_from'      : date_from,
            'date_to'        : date_to,
            'quantity'       : quantity,
            'amount'         : amount,
            'product_category_ids' : product_category_ids
        }
        docargs = {
                   'doc_model': 'low.sales.report',
                   'data': data,
                   'get_product_detail':self._get_product_detail,
                   }
        return docargs 
