# -*- coding: utf-8 -*-
# This module and its content is copyright of Technaureus Info Solutions Pvt. Ltd.
# - © Technaureus Info Solutions Pvt. Ltd 2020. All rights reserved.

from . import models
from . import report
from odoo import api, SUPERUSER_ID


def load_cost_post_init_hook(cr, registry):
    env = api.Environment(cr, SUPERUSER_ID, {})
    records = env['pos.order.line'].search([])
    for rec in records:
        rec.standard_price = rec.product_id.standard_price
