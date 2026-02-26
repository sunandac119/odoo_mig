# -*- coding: utf-8 -*-

from odoo import api, fields, models, _
from .forecasting import forecasting_details, forecasting_prediction


class SaleforecastingReport(models.Model):
    _name = "sale.forecasting.report"
    _description = "Sale Forecasting Report"

    forecasting_price = fields.Float("Total")
    forecasting_date = fields.Date("Order Date")
    name = fields.Char("Name")
    qty_ordered = fields.Float("Qty Ordered")
    qty_received = fields.Float("Qty Delivered")
    qty_billed = fields.Float('Qty Invoiced', readonly=True)

    def sale_forecasting_data(self):
        cr = self.env.cr

        # Delete Data
        cr.execute("""delete from sale_forecasting_report""")

        query_sales_data = """ 
            SELECT
                DATE(so.date_order) AS Dates,
                SUM(so.amount_total) AS Total,
                COALESCE(SUM(sol.product_uom_qty), 0) AS TotalOrderedQuantity,
                COALESCE(SUM(sol.qty_delivered), 0) AS TotalDeliveredQuantity,
                COALESCE(SUM(sol.qty_invoiced), 0) AS TotalInvoicedQuantity
            FROM
                sale_order so
            LEFT JOIN
                (
                    SELECT
                        order_id, 
                        SUM(product_uom_qty) AS product_uom_qty,
                        SUM(qty_delivered) AS qty_delivered,
                        SUM(qty_invoiced) AS qty_invoiced
                    FROM
                        sale_order_line
                    GROUP BY
                        order_id
                ) sol
            ON
                so.id = sol.order_id
            WHERE
                so.date_order <= CURRENT_DATE + INTERVAL '1 DAY'
            GROUP BY
                Dates
            ORDER BY
                Dates;
        """
        
        cr.execute(query_sales_data)
        forecasted_sale_data = forecasting_details(cr.fetchall())

        Obj = self.env['sale.forecasting.report']
        if forecasted_sale_data is not None:
            for item in forecasted_sale_data:
                info = dict()

                info['forecasting_date'] = item['Month'].strftime('%Y-%m-%d')

                total_value = item['Total']
                info['forecasting_price'] = 0.0 if total_value < 0.0 else total_value

                total_qty_ordered = item['Forecast_Qty_Ordered']
                info['qty_ordered'] = 0.0 if total_qty_ordered < 0.0 else total_qty_ordered

                total_qty_delivered= item['Forecast_Qty_Delivered']
                info['qty_received'] = 0.0 if total_qty_delivered < 0.0 else total_qty_delivered

                total_qty_invoiced = item['Forecast_Qty_Invoiced']
                info['qty_billed'] = 0.0 if total_qty_invoiced < 0.0 else total_qty_invoiced
       
                try:
                    Obj.sudo().create(info)
                except Exception as e:
                    print("Error Creating Record:", e)
        else:
            print("Insufficient Data")

class SalesPersonForecasting(models.Model):
    _name = 'salesperson.forecasting'
    _description = 'Forecasting for each salesperson'

    forecasting_month = fields.Date(string="Month")
    salesperson_id = fields.Many2one('res.users', string='Salesperson')

    total_forecasted_sale = fields.Float(string="Total")
    total_forecasted_qty_ordered = fields.Float(string="Qty Ordered")
    total_forecasted_qty_delivered = fields.Float(string="Qty Delivered")
    total_forecasted_qty_invoiced = fields.Float(string="Qty Invoiced")

    def saleperson_forecasting(self):
        cr = self.env.cr

        cr.execute("""delete from salesperson_forecasting""")

        query_salesperson_data = """
            SELECT
                initial_query.daily_sale_dates,
                initial_query.user_id,
                initial_query.sum_total,
                COALESCE(sq.sum_quantity, 0) AS sum_quantity,
                COALESCE(sq.sum_quantity_delivered, 0) AS sum_quantity_delivered,
                COALESCE(sq.total_invoiced_qty, 0) AS total_invoiced_qty
            FROM (
                SELECT
                    user_id,
                    DATE_TRUNC('day', date_order)::DATE AS daily_sale_dates,  -- Changed to 'day'
                    SUM(amount_total) AS sum_total
                FROM
                    sale_order
                GROUP BY
                    user_id,
                    daily_sale_dates
            ) AS initial_query
            LEFT JOIN (
                SELECT
                    so.user_id,
                    DATE_TRUNC('day', so.date_order)::DATE AS daily_sale_dates,  -- Changed to 'day'
                    SUM(sol.product_uom_qty) AS sum_quantity,
                    SUM(sol.qty_delivered) AS sum_quantity_delivered,
                    SUM(sol.qty_invoiced) as total_invoiced_qty
                FROM
                    sale_order so
                JOIN
                    sale_order_line sol ON so.id = sol.order_id
                GROUP BY
                    so.user_id,
                    daily_sale_dates
            ) AS sq ON initial_query.user_id = sq.user_id AND initial_query.daily_sale_dates = sq.daily_sale_dates
            ORDER BY
                initial_query.user_id,
                initial_query.daily_sale_dates;
        """

        cr.execute(query_salesperson_data)
        forecasted_sale = forecasting_prediction(cr.fetchall())

        Obj = self.env['salesperson.forecasting']
        for item in forecasted_sale:
            info = dict()

            info['forecasting_month'] = item['Month'].strftime('%Y-%m-%d')

            info['salesperson_id'] = item['Responsible']

            total_value = item['Total']
            info['total_forecasted_sale'] = 0.0 if total_value < 0.0 else total_value

            total_qty_ordered = item['Forecast_Qty_Ordered']
            info['total_forecasted_qty_ordered'] = 0.0 if total_qty_ordered < 0.0 else total_qty_ordered

            total_qty_delivered= item['Forecast_Qty_Delivered']
            info['total_forecasted_qty_delivered'] = 0.0 if total_qty_delivered < 0.0 else total_qty_delivered

            total_qty_invoiced = item['Forecast_Qty_Invoiced']
            info['total_forecasted_qty_invoiced'] = 0.0 if total_qty_invoiced < 0.0 else total_qty_invoiced

            try:
                Obj.sudo().create(info)
            except Exception as e:
                print("Error Creating Record:", e)


class SalesCustomerForecasting(models.Model):
    _name = 'salescustomer.forecasting'
    _description = 'Forecasting for each customer'

    forecasting_month = fields.Date(string="Month")
    customer_id = fields.Many2one('res.partner', string='Customer')

    total_forecasted_sale = fields.Float(string="Total")
    total_forecasted_qty_ordered = fields.Float(string="Qty Ordered")
    total_forecasted_qty_delivered = fields.Float(string="Qty Delivered")
    total_forecasted_qty_invoiced = fields.Float(string="Qty Invoiced")

    def salecustomer_forecasting(self):
        cr = self.env.cr

        cr.execute("""delete from salescustomer_forecasting""")

        query_salescustomer_data = """
            SELECT
                initial_query.daily_sale_dates,
                initial_query.partner_id,
                initial_query.sum_total,
                COALESCE(sq.sum_quantity, 0) AS sum_quantity,
                COALESCE(sq.sum_quantity_delivered, 0) AS sum_quantity_delivered,
                COALESCE(sq.total_invoiced_qty, 0) AS total_invoiced_qty
            FROM (
                SELECT
                    partner_id,
                    DATE_TRUNC('day', date_order)::DATE AS daily_sale_dates,  -- Changed to 'day'
                    SUM(amount_total) AS sum_total
                FROM
                    sale_order
                GROUP BY
                    partner_id,
                    daily_sale_dates
            ) AS initial_query
            LEFT JOIN (
                SELECT
                    so.partner_id,
                    DATE_TRUNC('day', so.date_order)::DATE AS daily_sale_dates,  -- Changed to 'day'
                    SUM(sol.product_uom_qty) AS sum_quantity,
                    SUM(sol.qty_delivered) AS sum_quantity_delivered,
                    SUM(sol.qty_invoiced) as total_invoiced_qty
                FROM
                    sale_order so
                JOIN
                    sale_order_line sol ON so.id = sol.order_id
                GROUP BY
                    so.partner_id,
                    daily_sale_dates
            ) AS sq ON initial_query.	partner_id = sq.partner_id AND initial_query.daily_sale_dates = sq.daily_sale_dates
            ORDER BY
                initial_query.partner_id,
                initial_query.daily_sale_dates;
        """

        cr.execute(query_salescustomer_data)
        forecasted_sale = forecasting_prediction(cr.fetchall())

        Obj = self.env['salescustomer.forecasting']
        for item in forecasted_sale:
            info = dict()

            info['forecasting_month'] = item['Month'].strftime('%Y-%m-%d')

            info['customer_id'] = item['Responsible']

            total_value = item['Total']
            info['total_forecasted_sale'] = 0.0 if total_value < 0.0 else total_value

            total_qty_ordered = item['Forecast_Qty_Ordered']
            info['total_forecasted_qty_ordered'] = 0.0 if total_qty_ordered < 0.0 else total_qty_ordered

            total_qty_delivered= item['Forecast_Qty_Delivered']
            info['total_forecasted_qty_delivered'] = 0.0 if total_qty_delivered < 0.0 else total_qty_delivered

            total_qty_invoiced = item['Forecast_Qty_Invoiced']
            info['total_forecasted_qty_invoiced'] = 0.0 if total_qty_invoiced < 0.0 else total_qty_invoiced

            try:
                Obj.sudo().create(info)
            except Exception as e:
                print("Error Creating Record:", e)


class SalesProductForecasting(models.Model):
    _name = 'salesproduct.forecasting'
    _description = 'Forecasting for each product'

    forecasting_month = fields.Date(string="Month")
    product_id = fields.Many2one('product.product', string='Product')

    total_forecasted_sale = fields.Float(string="Total")
    total_forecasted_qty_ordered = fields.Float(string="Qty Ordered")
    total_forecasted_qty_delivered = fields.Float(string="Qty Delivered")
    total_forecasted_qty_invoiced = fields.Float(string="Qty Invoiced")

    def saleproduct_forecasting(self):
        cr = self.env.cr

        cr.execute("""delete from salesproduct_forecasting""")

        query_salesproduct_data = """
             SELECT
                DATE_TRUNC('day', so.date_order)::DATE AS daily_sale_dates,
                sol.product_id as responsible,
                SUM(sol.price_subtotal) AS total_sum, 
                SUM(sol.product_uom_qty) AS total_qty,
                SUM(sol.qty_delivered) as total_delivered_qty,
                SUM(sol.qty_invoiced) as total_invoiced_qty
            FROM
                sale_order so
            JOIN
                sale_order_line sol ON so.id = sol.order_id
            GROUP BY
                sol.product_id,
                daily_sale_dates
            ORDER BY
                sol.product_id,
                daily_sale_dates;
        """

        cr.execute(query_salesproduct_data)
        forecasted_sale = forecasting_prediction(cr.fetchall())

        Obj = self.env['salesproduct.forecasting']
        for item in forecasted_sale:
            info = dict()

            info['forecasting_month'] = item['Month'].strftime('%Y-%m-%d')

            info['product_id'] = item['Responsible']

            total_value = item['Total']
            info['total_forecasted_sale'] = 0.0 if total_value < 0.0 else total_value

            total_qty_ordered = item['Forecast_Qty_Ordered']
            info['total_forecasted_qty_ordered'] = 0.0 if total_qty_ordered < 0.0 else total_qty_ordered

            total_qty_delivered= item['Forecast_Qty_Delivered']
            info['total_forecasted_qty_delivered'] = 0.0 if total_qty_delivered < 0.0 else total_qty_delivered

            total_qty_invoiced = item['Forecast_Qty_Invoiced']
            info['total_forecasted_qty_invoiced'] = 0.0 if total_qty_invoiced < 0.0 else total_qty_invoiced

            try:
                Obj.sudo().create(info)
            except Exception as e:
                print("Error Creating Record:", e)
                       