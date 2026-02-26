from odoo import api, fields, models, _
from .forecasting import forecasting_details, forecasting_prediction


class forecastingReportPurchase(models.Model):
    _name = "purchase.forecasting.report"
    _description = "Purchase Forecasting Report"

    forecasting_price = fields.Float("Total")
    forecasting_date = fields.Date("Order Date")
    name = fields.Char("Name")
    qty_ordered = fields.Float("Qty Ordered")
    qty_received = fields.Float("Qty Received")
    qty_billed = fields.Float('Qty Billed', readonly=True)

    def purchase_forecasting_data(self):
        cr = self.env.cr

        # delete existing data for new entries
        cr.execute("""delete from purchase_forecasting_report""")

        query_purchase_data = """ 
            SELECT
                DATE(po.date_order) AS Dates,
                SUM(po.amount_total) AS Total,
                COALESCE(SUM(pol.product_qty), 0) AS TotalOrderedQuantity,
                COALESCE(SUM(pol.qty_received), 0) AS TotalDeliveredQuantity,
                COALESCE(SUM(pol.qty_invoiced), 0) AS TotalInvoicedQuantity
            FROM
                purchase_order po
            LEFT JOIN
                (
                    SELECT
                        /* Replace 'order_id' with the correct column name */
                        order_id, 
                        SUM(product_qty) AS product_qty,
                        SUM(qty_received) AS qty_received,
                        SUM(qty_invoiced) AS qty_invoiced
                    FROM
                        purchase_order_line
                    GROUP BY
                        /* Replace 'order_id' with the correct column name */
                        order_id
                ) pol
            ON
                po.id = pol.order_id
            WHERE
                po.date_order <= CURRENT_DATE + INTERVAL '1 DAY'
            GROUP BY
                Dates
            ORDER BY
                Dates;
        """
        
        cr.execute(query_purchase_data)
        forecasted_purchase_data = forecasting_details(cr.fetchall())

        Obj = self.env['purchase.forecasting.report']
        if forecasted_purchase_data is not None:
            for item in forecasted_purchase_data:
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


class PurchasePersonForecasting(models.Model):
    _name = 'purchaseperson.forecasting'
    _description = 'Forecasting for each Purchase Representative'

    forecasting_month = fields.Date(string="Month")
    salesperson_id = fields.Many2one('res.users', string='Purchase Representative')

    total_forecasted_purchase = fields.Float(string="Total")
    total_forecasted_qty_ordered = fields.Float(string="Qty Ordered")
    total_forecasted_qty_received = fields.Float(string="Qty Received")
    total_forecasted_qty_invoiced = fields.Float(string="Qty Invoiced")

    def purchaseperson_forecasting(self):
        cr = self.env.cr

        cr.execute("""delete from purchaseperson_forecasting""")

        query_purchaseperson_data = """
            SELECT
                initial_query.month_sale_dates,
                initial_query.user_id,
                initial_query.sum_total,
                COALESCE(sq.sum_quantity_ordered, 0) AS sum_quantity_ordered,
                COALESCE(sq.sum_quantity_received, 0) AS sum_quantity_received,
                COALESCE(sq.sum_quantity_invoiced, 0) AS sum_quantity_invoiced
            FROM (
                SELECT
                    user_id,
                    DATE_TRUNC('day', date_order)::DATE AS month_sale_dates,
                    SUM(amount_total) AS sum_total
                FROM
                    purchase_order
                GROUP BY
                    user_id,
                    month_sale_dates
            ) AS initial_query
            LEFT JOIN (
                SELECT
                    po.user_id,
                    DATE_TRUNC('day', po.date_order)::DATE AS month_sale_dates,
                    SUM(pol.product_uom_qty) AS sum_quantity_ordered,
                    SUM(pol.qty_received) AS sum_quantity_received,
                    SUM(pol.qty_to_invoice) AS sum_quantity_invoiced
                FROM
                    purchase_order po
                JOIN
                    purchase_order_line pol ON po.id = pol.order_id
                GROUP BY
                    po.user_id,
                    month_sale_dates
            ) AS sq ON initial_query.user_id = sq.user_id AND initial_query.month_sale_dates = sq.month_sale_dates
            ORDER BY
                initial_query.user_id,
                initial_query.month_sale_dates;
        """

        cr.execute(query_purchaseperson_data)
        forecasted_purchase = forecasting_prediction(cr.fetchall())


        Obj = self.env['purchaseperson.forecasting']
        for item in forecasted_purchase:
            info = dict()

            info['forecasting_month'] = item['Month'].strftime('%Y-%m-%d')

            info['salesperson_id'] = item['Responsible']

            total_value = item['Total']
            info['total_forecasted_purchase'] = 0.0 if total_value < 0.0 else total_value

            total_qty_ordered = item['Forecast_Qty_Ordered']
            info['total_forecasted_qty_ordered'] = 0.0 if total_qty_ordered < 0.0 else total_qty_ordered

            total_qty_delivered= item['Forecast_Qty_Delivered']
            info['total_forecasted_qty_received'] = 0.0 if total_qty_delivered < 0.0 else total_qty_delivered

            total_qty_invoiced = item['Forecast_Qty_Invoiced']
            info['total_forecasted_qty_invoiced'] = 0.0 if total_qty_invoiced < 0.0 else total_qty_invoiced

            try:
                Obj.sudo().create(info)
            except Exception as e:
                print("Error Creating Record:", e)


class PurchaseVendorForecasting(models.Model):
    _name = 'purchasevendor.forecasting'
    _description = 'Forecasting for each Vendor'

    forecasting_month = fields.Date(string="Month")
    customer_id = fields.Many2one('res.partner', string='Vendor')

    total_forecasted_purchase = fields.Float(string="Total")
    total_forecasted_qty_ordered = fields.Float(string="Qty Ordered")
    total_forecasted_qty_received = fields.Float(string="Qty Received")
    total_forecasted_qty_invoiced = fields.Float(string="Qty Invoiced")

    def purchasevendor_forecasting(self):
        cr = self.env.cr

        cr.execute("""delete from purchasevendor_forecasting""")

        query_purchasevendor_data = """
            SELECT
                initial_query.month_sale_dates,
                initial_query.partner_id,
                initial_query.sum_total,
                COALESCE(sq.sum_quantity_ordered, 0) AS sum_quantity_ordered,
                COALESCE(sq.sum_quantity_received, 0) AS sum_quantity_received,
                COALESCE(sq.sum_quantity_invoiced, 0) AS sum_quantity_invoiced
            FROM (
                SELECT
                    partner_id,
                    DATE_TRUNC('day', date_order)::DATE AS month_sale_dates,
                    SUM(amount_total) AS sum_total
                FROM
                    purchase_order
                GROUP BY
                    partner_id,
                    month_sale_dates
            ) AS initial_query
            LEFT JOIN (
                SELECT
                    po.partner_id,
                    DATE_TRUNC('day', po.date_order)::DATE AS month_sale_dates,
                    SUM(pol.product_uom_qty) AS sum_quantity_ordered,
                    SUM(pol.qty_received) AS sum_quantity_received,
                    SUM(pol.qty_to_invoice) AS sum_quantity_invoiced
                FROM
                    purchase_order po
                JOIN
                    purchase_order_line pol ON po.id = pol.order_id
                GROUP BY
                    po.partner_id,
                    month_sale_dates
            ) AS sq ON initial_query.partner_id = sq.partner_id AND initial_query.month_sale_dates = sq.month_sale_dates
            ORDER BY
                initial_query.partner_id,
                initial_query.month_sale_dates;
        """

        cr.execute(query_purchasevendor_data)
        forecasted_purchase = forecasting_prediction(cr.fetchall())
        
        Obj = self.env['purchasevendor.forecasting']
        for item in forecasted_purchase:
            info = dict()

            info['forecasting_month'] = item['Month'].strftime('%Y-%m-%d')

            info['customer_id'] = item['Responsible']

            total_value = item['Total']
            info['total_forecasted_purchase'] = 0.0 if total_value < 0.0 else total_value

            total_qty_ordered = item['Forecast_Qty_Ordered']
            info['total_forecasted_qty_ordered'] = 0.0 if total_qty_ordered < 0.0 else total_qty_ordered

            total_qty_delivered= item['Forecast_Qty_Delivered']
            info['total_forecasted_qty_received'] = 0.0 if total_qty_delivered < 0.0 else total_qty_delivered

            total_qty_invoiced = item['Forecast_Qty_Invoiced']
            info['total_forecasted_qty_invoiced'] = 0.0 if total_qty_invoiced < 0.0 else total_qty_invoiced

            try:
                Obj.sudo().create(info)
            except Exception as e:
                print("Error Creating Record:", e)

class PurchaseProductForecasting(models.Model):
    _name = 'purchaseproduct.forecasting'
    _description = 'Forecasting for each product'

    forecasting_month = fields.Date(string="Month")
    product_id = fields.Many2one('product.product', string='Product')

    total_forecasted_purchase = fields.Float(string="Total")
    total_forecasted_qty_ordered = fields.Float(string="Qty Ordered")
    total_forecasted_qty_received = fields.Float(string="Qty Delivered")
    total_forecasted_qty_invoiced = fields.Float(string="Qty Invoiced")

    def purchaseproduct_forecasting(self):
        cr = self.env.cr

        cr.execute("""delete from purchaseproduct_forecasting""")

        query_purhcaseproduct_data = """ 
            SELECT
                DATE_TRUNC('day', po.date_order)::DATE AS daily_sale_dates,
                pol.product_id as responsible,
                SUM(pol.price_subtotal) AS total_sum, 
                SUM(pol.product_uom_qty) AS total_qty,
                SUM(pol.qty_received) as total_delivered_qty,
                SUM(pol.qty_invoiced) as total_invoiced_qty
            FROM
                purchase_order po
            JOIN
                purchase_order_line pol  ON po.id = pol.order_id
            GROUP BY
                pol.product_id,
                daily_sale_dates
            ORDER BY
                pol.product_id,
                daily_sale_dates;
        """

        cr.execute(query_purhcaseproduct_data)
        forecasted_purchase = forecasting_prediction(cr.fetchall())
        print(forecasted_purchase,'\n\n\n')

        Obj = self.env['purchaseproduct.forecasting']
        for item in forecasted_purchase:
            info = dict()

            info['forecasting_month'] = item['Month'].strftime('%Y-%m-%d')

            info['product_id'] = item['Responsible']

            total_value = item['Total']
            info['total_forecasted_purchase'] = 0.0 if total_value < 0.0 else total_value

            total_qty_ordered = item['Forecast_Qty_Ordered']
            info['total_forecasted_qty_ordered'] = 0.0 if total_qty_ordered < 0.0 else total_qty_ordered

            total_qty_delivered= item['Forecast_Qty_Delivered']
            info['total_forecasted_qty_received'] = 0.0 if total_qty_delivered < 0.0 else total_qty_delivered

            total_qty_invoiced = item['Forecast_Qty_Invoiced']
            info['total_forecasted_qty_invoiced'] = 0.0 if total_qty_invoiced < 0.0 else total_qty_invoiced

            try:
                Obj.sudo().create(info)
            except Exception as e:
                print("Error Creating Record:", e)

        