# -*- coding: utf-8 -*-
# from odoo import http


# class MrpCost(http.Controller):
#     @http.route('/mrp_cost/mrp_cost/', auth='public')
#     def index(self, **kw):
#         return "Hello, world"

#     @http.route('/mrp_cost/mrp_cost/objects/', auth='public')
#     def list(self, **kw):
#         return http.request.render('mrp_cost.listing', {
#             'root': '/mrp_cost/mrp_cost',
#             'objects': http.request.env['mrp_cost.mrp_cost'].search([]),
#         })

#     @http.route('/mrp_cost/mrp_cost/objects/<model("mrp_cost.mrp_cost"):obj>/', auth='public')
#     def object(self, obj, **kw):
#         return http.request.render('mrp_cost.object', {
#             'object': obj
#         })
