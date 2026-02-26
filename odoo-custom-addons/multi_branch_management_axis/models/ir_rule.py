# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.
import hashlib
import json

from odoo import api, models
from odoo.http import request
from odoo.tools import ustr

# from odoo.addons.web.controllers.main import module_boot, HomeStaticTemplateHelpers

import odoo


class IrRule(models.AbstractModel):
    _inherit = 'ir.rule'

    @api.model
    def _eval_context(self):
        print("\n in my ir_rule:")
        res = super(IrRule, self)._eval_context()
        res.update(
            {
                # 'branch_id': self.env.branch.id,
                'branch_id': self.env.user.branch_id.id,
                # 'branch_ids': self.env.branchies.ids,
                'branch_ids': self.env.user.branch_ids.ids,
                'multi_branch_id': self.env.user.multi_branch_id.ids
            }
        )
        print("multi_branch_id:",self.env.user.multi_branch_id)
        print("res:", res)
        return res

    def _compute_domain_keys(self):
        # print("\nin side comute domainkeys:..:", self)
        res = super(IrRule, self)._compute_domain_keys()
        # print("fiest res:.:", res)
        res.append('allowed_branch_ids')
        # print("last res:.:", res)

        return res



