# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.
import hashlib
import json

from odoo import api, models
from odoo.http import request
from odoo.tools import ustr

from odoo.addons.web.controllers.main import module_boot, HomeStaticTemplateHelpers

import odoo


class Http(models.AbstractModel):
    _inherit = 'ir.http'


    def session_info(self):
        print("\n2 session info:.inherited.:", )
        user = request.env.user
        company = request.env.company
        print("\n \n\n   session_info   request.session:", request.session)
        print ("\n\n   self.context.get('allowed_branch_ids', []) ",  request._context)
        print ("\n\n   self._context ",  self._context)

        print("session_info   user:", user, user.name)
        user_context = request.session.get_context() if request.session.uid else {}
        # user_context['allowed_branch_ids'] = [[branch.id, branch.name] for branch in user.branch_ids]
        user_context['allowed_branch_ids'] = [branch.id for branch in user.branch_ids if branch.id == user.branch_id.id]
        user_context['allowed_branches'] = [(branch_id.id, branch_id.name) for branch_id in user.branch_ids]
        print("\nmy  user_context:", user_context)
        res = super(Http, self).session_info()
        print("\n\n session_info    res:...:", res)

        print("\n")
        res.update({
            'branch_id': user.branch_id.id if request.session.uid else None,
            "user_branches": {'current_branch': (user.branch_id.id, user.branch_id.name),
                               'allowed_branches': [(branch.id, branch.name) for branch in user.branch_ids]},
            "show_effect": True,
            "allowed_branch_ids" : [branch.id for branch in user.branch_ids if branch.id == user.branch_id.id],
            'allowed_branches' : [(branch_id.id, branch_id.name) for branch_id in user.branch_ids],
            # 'allowed_branches' : [(branch_id.id, branch_id.name) for branch_id in user.multi_branch_id],
            "display_switch_branch_menu": user.has_group('multi_branch_management_axis.group_multi_branch') and len(user.branch_ids) > 1,
        })
        print ("\n\n\n >>>>>>>>>    47       >>>>>>>>>.session nfo ---> res. ",res)
        print ("\n\n>>>>>>>>>>>>>>>>>>.session nfo ---> user.branch_id   user_branches ",res['user_branches'])
        print (">>>>>>>>>>>>>>>>>>.session nfo ---> user.branch_id   user_branches ",res['user_branches'])
        res['user_context'] = user_context
        print("\n\n -session_info   -- res branch :", res)
        return res
