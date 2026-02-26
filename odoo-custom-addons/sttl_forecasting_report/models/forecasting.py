# -*- coding: utf-8 -*-
import pandas as pd
from statsmodels.tsa.api import ExponentialSmoothing
import warnings


def forecasting_details(sql_result):
    data = pd.DataFrame(sql_result, columns=["month_date", "sum", "qty_ordered", "qty_delivered", "qty_invoiced"])

    # Forecasting for each product
    forecast_periods = 12  # Forecasting for the next 12 months
    forecast_results = []

    if(len(data)) >= 2:
        
        # seasonal forecasting if enough data
        try:
            model_total = ExponentialSmoothing(
                data['sum'].astype(float), trend='add', seasonal='add', seasonal_periods=12)
            model_fit_total = model_total.fit()

            model_qty = ExponentialSmoothing(
                data['qty_ordered'].astype(float), trend='add', seasonal='add', seasonal_periods=12)
            model_fit_qty_ordered = model_qty.fit()

            model_qty_delivered = ExponentialSmoothing(
                data['qty_delivered'].astype(float), trend='add', seasonal='add', seasonal_periods=12)
            model_fit_qty_delivered = model_qty_delivered.fit()

            model_qty_invoiced = ExponentialSmoothing(
                data['qty_invoiced'].astype(float), trend='add', seasonal='add', seasonal_periods=12)
            model_fit_qty_invoiced = model_qty_invoiced.fit()


        except Exception as e:
            warnings.warn(f"Error for product {data} when adding seasonality: {str(e)}")

            model_total = ExponentialSmoothing(
                data['sum'].astype(float), trend='add', seasonal_periods=12)
            model_fit_total = model_total.fit()

            model_qty = ExponentialSmoothing(
                data['qty_ordered'].astype(float), trend='add', seasonal_periods=12)
            model_fit_qty_ordered = model_qty.fit()

            model_qty_delivered = ExponentialSmoothing(
                data['qty_delivered'].astype(float), trend='add', seasonal_periods=12)
            model_fit_qty_delivered = model_qty_delivered.fit()

            model_qty_invoiced = ExponentialSmoothing(
                data['qty_invoiced'].astype(float), trend='add', seasonal_periods=12)
            model_fit_qty_invoiced = model_qty_invoiced.fit()

         # Forecast the next 12 months
        forecast_values_total = model_fit_total.forecast(steps=forecast_periods).tolist()
        forecast_values_qty_ordered = model_fit_qty_ordered.forecast(steps=forecast_periods).tolist()
        forecast_values_qty_delivered = model_fit_qty_delivered.forecast(steps=forecast_periods).tolist()
        forecast_values_qty_invoiced = model_fit_qty_invoiced.forecast(steps=forecast_periods).tolist()

        # Generate the date range for the forecast (next 12 months)
        last_date = data['month_date'].max()
        forecast_dates = pd.date_range(
            start=last_date, periods=forecast_periods, freq='MS')

        # Create a list of dictionaries to store the forecast results for the current product
        forecast_dicts = []
        for i in range(forecast_periods):
            forecast_dict = {
                'Month': forecast_dates[i],
                'Total': forecast_values_total[i],
                'Forecast_Qty_Ordered': forecast_values_qty_ordered[i],
                'Forecast_Qty_Delivered': forecast_values_qty_delivered[i],
                'Forecast_Qty_Invoiced': forecast_values_qty_invoiced[i],
            }
            forecast_dicts.append(forecast_dict)

        # Append the current product's forecast dictionaries to the list
        forecast_results.extend(forecast_dicts)

    else:
        print(f"Skipping data due to insufficient data points.")

    return forecast_results

def forecasting_prediction(sql_result):

    data = pd.DataFrame(sql_result, columns=["month_date", "responsible", "sum", "qty_ordered", "qty_delivered", "qty_invoiced"])

    # Forecasting for each product
    forecast_periods = 12  # Forecasting for the next 12 months
    forecast_results = []

    for name, total in data.groupby('responsible'):

        if len(total) >= 2:
            try:
                model_total = ExponentialSmoothing(
                    total['sum'].astype(float), trend='add', seasonal='add', seasonal_periods=12)
                model_fit_total = model_total.fit()

                model_qty = ExponentialSmoothing(
                    total['qty_ordered'].astype(float), trend='add', seasonal='add', seasonal_periods=12)
                model_fit_qty_ordered = model_qty.fit()

                model_qty_delivered = ExponentialSmoothing(
                    total['qty_delivered'].astype(float), trend='add', seasonal='add', seasonal_periods=12)
                model_fit_qty_delivered = model_qty_delivered.fit()

                model_qty_invoiced = ExponentialSmoothing(
                    total['qty_invoiced'].astype(float), trend='add', seasonal='add', seasonal_periods=12)
                model_fit_qty_invoiced = model_qty_invoiced.fit()

            except Exception as e:
                warnings.warn(f"Error for product {name} when adding seasonality: {str(e)}")

                model_total = ExponentialSmoothing(
                    total['sum'].astype(float), trend='add', seasonal_periods=12)
                model_fit_total = model_total.fit()

                model_qty = ExponentialSmoothing(
                    total['qty_ordered'].astype(float), trend='add', seasonal_periods=12)
                model_fit_qty_ordered = model_qty.fit()

                model_qty_delivered = ExponentialSmoothing(
                    total['qty_delivered'].astype(float), trend='add', seasonal_periods=12)
                model_fit_qty_delivered = model_qty_delivered.fit()

                model_qty_invoiced = ExponentialSmoothing(
                    total['qty_invoiced'].astype(float), trend='add', seasonal_periods=12)
                model_fit_qty_invoiced = model_qty_invoiced.fit()

            # Forecast the next 12 months
            forecast_values_total = model_fit_total.forecast(steps=forecast_periods).tolist()
            forecast_values_qty_ordered = model_fit_qty_ordered.forecast(steps=forecast_periods).tolist()
            forecast_values_qty_delivered = model_fit_qty_delivered.forecast(steps=forecast_periods).tolist()
            forecast_values_qty_invoiced = model_fit_qty_invoiced.forecast(steps=forecast_periods).tolist()

            # Generate the date range for the forecast (next 12 months)
            last_date = data['month_date'].max()
            forecast_dates = pd.date_range(
                start=last_date, periods=forecast_periods, freq='MS')

            # Create a list of dictionaries to store the forecast results for the current product
            forecast_dicts = []
            for i in range(forecast_periods):
                forecast_dict = {
                    'Month': forecast_dates[i],
                    'Responsible': name,
                    'Total': forecast_values_total[i],
                    'Forecast_Qty_Ordered': forecast_values_qty_ordered[i],
                    'Forecast_Qty_Delivered': forecast_values_qty_delivered[i],
                    'Forecast_Qty_Invoiced': forecast_values_qty_invoiced[i],
                }
                forecast_dicts.append(forecast_dict)

            # Append the current product's forecast dictionaries to the list
            forecast_results.extend(forecast_dicts)
        
        else:
            print(f"Skipping data with id {name} due to insufficient data points.")
    return forecast_results