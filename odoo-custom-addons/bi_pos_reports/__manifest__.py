# -*- coding: utf-8 -*-
# Part of BrowseInfo. See LICENSE file for full copyright and licensing details.

{
	"name" : "ALL POS Reports in Odoo (POS BOX Compatible)",
	"version" : "14.0.0.0",
	"category" : "Point of Sale",
	"depends" : ['base','sale','point_of_sale'],
	"author": "Businesscontrol",
	'summary': 'All in one pos reports Print pos session report pos sales summery report pos sales reports point of sales reports pos X Report pos z report pos payment summary reports pos Inventory audit report pos Order summary report pos Posted Session POS Profit Report',
	"description": """
	odoo Print POS Reports print pos reports odoo all in one pos reports
    odoo point of sales reports pos reports print pos report print
	odoo pos sales summary report pos summary report pos Session and Inventory audit report
    odoo pos audit report pos Product summary report
     odoo pos sessions reports pos session reports pos User wise sales summary reports
     odoo pos payment summary reports summary reports in POS
     odoo point of sales summary reports point of sales reports pos user reports
     odoo point of sales all reports pos products reports pos audit reports audit reports pos 
	odoo pos Inventory audit reports pos Inventory reports Product summary report pos 

		odoo Print point of sales Reports print point of sales reports odoo all in one point of sales reports
    odoo point of sale reports point of sales reports print point of sales report print
	odoo point of sale summary report point of sales summary report point of sales Session and Inventory audit report
    odoo point of sales audit report point of sale Product summary report
     odoo point of sales sessions reports point of sales session reports point of sales User wise sales summary reports
     odoo pos payment summary reports summary reports in POS
     odoo point of sales summary reports point of sales reports point of sales user reports
     odoo point of sale all reports point of sales products reports point of sales audit reports audit reports point of sales 
	odoo point of sales Inventory audit reports point of sales Inventory reports Product summary report point of sales 



	""",
	"website" : "https://www.businesscontrol.com.mx",
	"price": 00,
	"currency": "MXN",
	"data": [
		'security/ir.model.access.csv',
		'views/pos_reports_assets.xml',
		'wizard/pos_payment_report.xml',
		'wizard/pos_payment.xml',
	],
	'qweb': [
		'static/src/xml/pos_reports.xml',
	],
	"auto_install": False,
	"installable": True,
	"images":['static/description/Banner.png'],
	"live_test_url":'https://youtu.be/Y5t_EZJxymY',
}
# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:
