from odoo import fields,models,api,_

class ResCompany(models.Model):
    _inherit = "res.company"

    report_header_tilte = fields.Char('Report Header Title')


class PrintCategoryClonetReport(models.AbstractModel):
    _name = 'report.mai_pos_advance_report.print_category_clonet'
    _description = "Print Category Clonet Report"

    @api.model
    def _get_report_values(self, docids, data=None):
        return {
            'doc_ids': docids,
            'doc_model': 'pos.order',
            'lines': data.get('filter_data'),
            'company_id': self.env.user.company_id
        }


class PrintProductClonetReport(models.AbstractModel):
    _name = 'report.mai_pos_advance_report.print_product_clonet'
    _description = "Print Product Clonet Report"

    @api.model
    def _get_report_values(self, docids, data=None):
        return {
            'doc_ids': docids,
            'doc_model': 'pos.order',
            'lines': data.get('filter_data'),
            'company_id': self.env.user.company_id
        }


class PrintProductStockClonetReport(models.AbstractModel):
    _name = 'report.mai_pos_advance_report.print_product_stock_clonet'
    _description = "Print Product Stock Clonet Report"

    @api.model
    def _get_report_values(self, docids, data=None):
        return {
            'doc_ids': docids,
            'doc_model': 'pos.order',
            'lines': data.get('filter_data'),
            'company_id': self.env.user.company_id
        }


class PrintPOSPaymentClonetReport(models.AbstractModel):
    _name = 'report.mai_pos_advance_report.print_pos_payment_clonet'
    _description = "Print POS Payment Clonet Report"

    @api.model
    def _get_report_values(self, docids, data=None):
        res = {
            'doc_ids': docids,
            'doc_model': 'pos.order',
            'lines': data.get('filter_data'),
            'payment_method_list': data.get('payment_method_list'),
            'company_id': self.env.user.company_id,
            'payment_method_ids': data.get('payment_method_ids'),
            'get_payment_method_total': self.get_order_paymnet_method(data.get('filter_data')),
            'get_order_paymnet_method_summary': self.get_order_paymnet_method_summary(data.get('filter_data'))
        }
        return res

    def get_order_paymnet_method(self, data):
        final_amount = 0.0
        order_ids = [d.get('order_id') for d in data]
        pos_payment_obj = self.env['pos.payment']
        data_dict = {}
        pay_ids = self.env['pos.payment.method'].search([])
        total = 0.0
        for p in pay_ids:
            absl_ids = pos_payment_obj.search([('pos_order_id', 'in', order_ids), ('payment_method_id', '=', p.id)])
            final_amount = sum([absl_id.amount for absl_id in absl_ids])
            data_dict.update({p.id: final_amount})
            total += final_amount
        final_list = []
        for i in data_dict:
            final_list.append(data_dict.get(i))
        final_list.append(total)
        return final_list

    def get_order_paymnet_method_summary(self, data):
        final_amount = 0.0
        order_ids = [d.get('order_id') for d in data]
        pos_payment_obj = self.env['pos.payment']
        data_dict = {}
        pay_ids = self.env['pos.payment.method'].search([])
        for p in pay_ids:
            absl_ids = pos_payment_obj.search([('pos_order_id', 'in', order_ids), ('payment_method_id', '=', p.id)])
            final_amount = sum([absl_id.amount for absl_id in absl_ids])
            data_dict.update({p.id: {'name': p.name, 'amount': final_amount}})
        final_list = []
        for i in data_dict:
            final_list.append(data_dict.get(i))
        return final_list


class POSOrder(models.Model):
    _inherit = "pos.order"

    def get_order_paymnet_method(self, payment_id):
        final_amount = 0.0
        pos_payment_obj = self.env['pos.payment']
        pay_ids = self.env['pos.payment.method'].search([])
        for p in pay_ids:
            if payment_id == p.id:
                absl_ids = pos_payment_obj.search([('pos_order_id', '=', self.id), ('payment_method_id', '=', p.id)])
                final_amount = sum([absl_id.amount for absl_id in absl_ids])
        return final_amount
