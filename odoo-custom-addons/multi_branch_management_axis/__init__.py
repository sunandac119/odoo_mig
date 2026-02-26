# -*- coding: utf-8 -*-

from . import models
from . import controllers
from . import wizard
from . import report


from odoo.api import Environment, SUPERUSER_ID

def post_init_hook(cr, registry):
    env = Environment(cr, SUPERUSER_ID, {})
   
    main_branch_id = env.ref('multi_branch_management_axis.main_branch')
    print (">>>>>>>>>>>>>>>>>>>> post_init_hook main_branch_id ", main_branch_id)
    res_user_ids = env['res.users'].search([])
    for res_user_id in res_user_ids:
        res_user_id.write({
            'branch_id': main_branch_id.id,
            'branch_ids': [(6, 0, main_branch_id.ids)],
            'multi_branch_id': [(6, 0, main_branch_id.ids)],
            })
        
