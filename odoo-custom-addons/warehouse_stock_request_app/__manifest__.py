# -*- coding: utf-8 -*-

{
    'name' : 'Inventory Stock Request | Stock Request for Warehouse | Warehouse Internal Transfer | Stock Request for Internal Transfer | Inventory Internal Transfer',
    'author': "Edge Technologies",
    'version' : '14.0.1.0',
    'live_test_url':'https://youtu.be/XQUdrE9IKyI',
    "images":['static/description/main_screenshot.png'],
    'summary' : 'Warehouse inventory stock requests for warehouse stock internal transfer requests for inventory warehouse internal stock transfer warehouse stock transfer request inventory stock internal transfer internal warehouse stock transfer request for inventory',
    'description' : """
       Odoo inventory warehouse stock request app allows users can create new stock requests directly, specifying the required items, quantities, 
       and any additional information related to the request. Users can track the status of their stock requests in real time. 
       The app provides visibility into the approval stage and fulfillment progress. The manager can approve the stock request of the user. 
       The user and manager can send the mail of stock requests. The user and manager can generate stock request Information pdf reports.
     """,
    "license" : "OPL-1",
    'depends': ['base','stock','multi_branch_management_axis'],
    'data': [
        'security/ir.model.access.csv',
        'data/ir_sequence_data.xml',
        'report/stock_request_report.xml',
        'report/stock_request_report_view.xml',
        'data/template_views.xml',
        'views/warhouse_stock_request_views.xml',

    ],
    'qweb' : [
    ],
    'installable' : True,
    'auto_install' : False,
    'price': 20,
    'currency': "EUR",
    'category' : 'warehouse',
}
