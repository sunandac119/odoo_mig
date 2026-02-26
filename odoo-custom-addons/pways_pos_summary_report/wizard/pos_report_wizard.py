# -*- coding: utf-8 -*-
from odoo import models, fields, api, _
from odoo.exceptions import UserError, ValidationError


class PosReportWizard(models.TransientModel):
    _name = 'pos.report.wizard'
    _description = 'POS Summart report wizard'

    start_at = fields.Date(string='From Date', required=True)
    stop_at = fields.Date(string="To Date", required=True)
    shop_ids = fields.Many2many('pos.config', string="Shops")

    def print_pos_report_xls(self):
        if self.start_at > self.stop_at:
            raise ValidationError(_('Invalid date !'))
        data = {
            'start_at': self.start_at,
            'stop_at': self.stop_at,
            'shop_ids': self.shop_ids.ids,
        }
        return self.env.ref('pways_pos_summary_report.pos_xlsx').report_action(self, data=data)
