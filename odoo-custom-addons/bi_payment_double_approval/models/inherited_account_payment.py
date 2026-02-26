# -*- coding: utf-8 -*-
# Part of Browseinfo. See LICENSE file for full copyright and licensing details.

from odoo import api, fields, models, _
from odoo.exceptions import AccessError, UserError,ValidationError

class AccountMove(models.Model):
    _inherit = 'account.move'


    state = fields.Selection(selection_add=[
        ('first_approve', 'First Approval'),
        ('second_approve', 'Second Approval')
    ],ondelete={'first_approve': 'set default','second_approve':'set default'})



class AccountMoveLine(models.Model):
    _inherit = 'account.move.line'

    def reconcile(self):
        ''' Reconcile the current move lines all together.
        :return: A dictionary representing a summary of what has been done during the reconciliation:
                * partials:             A recorset of all account.partial.reconcile created during the reconciliation.
                * full_reconcile:       An account.full.reconcile record created when there is nothing left to reconcile
                                        in the involved lines.
                * tax_cash_basis_moves: An account.move recordset representing the tax cash basis journal entries.
        '''
        results = {}

        if not self:
            return results

        # List unpaid invoices
        not_paid_invoices = self.move_id.filtered(
            lambda move: move.is_invoice(include_receipts=True) and move.payment_state not in ('paid', 'in_payment')
        )

        # ==== Check the lines can be reconciled together ====
        company = None
        account = None
        for line in self:
            if line.reconciled:
                raise UserError(_("You are trying to reconcile some entries that are already reconciled."))
            if not line.account_id.reconcile and line.account_id.internal_type != 'liquidity':
                raise UserError(_("Account %s does not allow reconciliation. First change the configuration of this account to allow it.")
                                % line.account_id.display_name)
            
            if line.payment_id.account_first_approval or line.payment_id.account_second_approval:
                continue
            else:
                if line.move_id.state != 'posted':
                    raise UserError(_('You can only reconcile posted entries.'))


            if company is None:
                company = line.company_id
            elif line.company_id != company:
                raise UserError(_("Entries doesn't belong to the same company: %s != %s")
                                % (company.display_name, line.company_id.display_name))
            if account is None:
                account = line.account_id
            elif line.account_id != account:
                raise UserError(_("Entries are not from the same account: %s != %s")
                                % (account.display_name, line.account_id.display_name))

        sorted_lines = self.sorted(key=lambda line: (line.date_maturity or line.date, line.currency_id))

        # ==== Collect all involved lines through the existing reconciliation ====

        involved_lines = sorted_lines
        involved_partials = self.env['account.partial.reconcile']
        current_lines = involved_lines
        current_partials = involved_partials
        while current_lines:
            current_partials = (current_lines.matched_debit_ids + current_lines.matched_credit_ids) - current_partials
            involved_partials += current_partials
            current_lines = (current_partials.debit_move_id + current_partials.credit_move_id) - current_lines
            involved_lines += current_lines

        # ==== Create partials ====

        partials = self.env['account.partial.reconcile'].create(sorted_lines._prepare_reconciliation_partials())

        # Track newly created partials.
        results['partials'] = partials
        involved_partials += partials

        # ==== Create entries for cash basis taxes ====

        is_cash_basis_needed = account.user_type_id.type in ('receivable', 'payable')
        if is_cash_basis_needed and not self._context.get('move_reverse_cancel'):
            tax_cash_basis_moves = partials._create_tax_cash_basis_moves()
            results['tax_cash_basis_moves'] = tax_cash_basis_moves

        # ==== Check if a full reconcile is needed ====

        if involved_lines[0].currency_id and all(line.currency_id == involved_lines[0].currency_id for line in involved_lines):
            is_full_needed = all(line.currency_id.is_zero(line.amount_residual_currency) for line in involved_lines)
        else:
            is_full_needed = all(line.company_currency_id.is_zero(line.amount_residual) for line in involved_lines)

        if is_full_needed:

            # ==== Create the exchange difference move ====

            if self._context.get('no_exchange_difference'):
                exchange_move = None
            else:
                exchange_move = involved_lines._create_exchange_difference_move()
                if exchange_move:
                    exchange_move_lines = exchange_move.line_ids.filtered(lambda line: line.account_id == account)

                    # Track newly created lines.
                    involved_lines += exchange_move_lines

                    # Track newly created partials.
                    exchange_diff_partials = exchange_move_lines.matched_debit_ids \
                                             + exchange_move_lines.matched_credit_ids
                    involved_partials += exchange_diff_partials
                    results['partials'] += exchange_diff_partials

                    exchange_move._post(soft=False)

            # ==== Create the full reconcile ====

            results['full_reconcile'] = self.env['account.full.reconcile'].create({
                'exchange_move_id': exchange_move and exchange_move.id,
                'partial_reconcile_ids': [(6, 0, involved_partials.ids)],
                'reconciled_line_ids': [(6, 0, involved_lines.ids)],
            })

        # Trigger action for paid invoices
        not_paid_invoices\
            .filtered(lambda move: move.payment_state in ('paid', 'in_payment'))\
            .action_invoice_paid()

        return results

class AccountPayment(models.Model):
    _inherit = 'account.payment'

    account_first_approval = fields.Boolean(compute='_check_first_approval', string="First Approval",readonly=False)
    account_second_approval = fields.Boolean(compute='_check_second_approval', string="Second Approval",readonly=False)
    approval_customer = fields.Boolean(compute='_check_second_approval',string="Is Customer",readonly=False)
    approval_vendor = fields.Boolean(compute='_check_second_approval',string="Is Vendor",readonly=False)

    @api.depends('amount')
    def _check_first_approval(self):
        res_config = self.env['res.config.settings'].sudo().search([], order="id desc", limit=1)
        for payment in self:
            payment.update({'account_first_approval' : False})
            if res_config.account_first_approval and not res_config.account_second_approval:
                if res_config.approval_customer and payment.partner_type  == 'customer':
                    if payment.amount >= res_config.account_first_approval_minimum_amount:
                        payment.update({
                            'account_first_approval' : True,
                            'approval_customer' : True,
                        })
                elif res_config.approval_vendor and payment.partner_type  == 'supplier':
                    if payment.amount >= res_config.account_first_approval_minimum_amount:
                    
                        payment.update({
                            'account_first_approval' : True,
                            'approval_vendor' : True,
                        })
            elif res_config.account_first_approval and res_config.account_second_approval:
                if res_config.approval_customer and payment.partner_type  == 'customer':
                    if payment.amount >= res_config.account_first_approval_minimum_amount: 

                        payment.update({
                            'account_first_approval' : True,
                            'approval_customer' : True,
                        })
                elif res_config.approval_vendor and payment.partner_type  == 'supplier':
                    if payment.amount >= res_config.account_first_approval_minimum_amount :
                        payment.update({
                            'account_first_approval' : True,
                            'approval_vendor' : True,
                        })

    @api.depends('amount')
    def _check_second_approval(self):
        res_config = self.env['res.config.settings'].sudo().search([], order="id desc", limit=1)
        for payment in self:
            payment.update({'account_second_approval' : False})
            if res_config.account_second_approval == True:
                if res_config.approval_customer and payment.partner_type  == 'customer':
                    if payment.amount >= res_config.account_second_approval_minimum_amount:
                        payment.account_second_approval = True
                        payment.update({
                            'account_second_approval' : True,
                            'approval_customer' : True
                        })
                elif res_config.approval_vendor and payment.partner_type  == 'supplier':
                    if payment.amount >= res_config.account_second_approval_minimum_amount:
                        payment.account_second_approval = True
                        payment.update({
                            'account_second_approval' : True,
                            'approval_vendor' : True
                        })

    def action_post(self):
        # First Approval
        for payment in self:
            if payment.account_first_approval:
                # Payment First Approval AND Not Billing Manager
                if self.env.user.has_group('bi_payment_double_approval.group_payment_first_approval') and \
                    not self.env.user.has_group('account.group_account_manager'):
                    raise AccessError(_("Sorry, you are not allowed to access this document."))
                # Not Payment First Approval AND Not Billing Manager
                elif not self.env.user.has_group('bi_payment_double_approval.group_payment_first_approval') and \
                    not self.env.user.has_group('account.group_account_manager'):
                    raise AccessError(_("Sorry, you are not allowed to access this document."))
                else:
                    # Not Payment First Approval AND Billing Manager
                    if not self.env.user.has_group('bi_payment_double_approval.group_payment_first_approval') and \
                        self.env.user.has_group('account.group_account_manager'):
                        raise AccessError(_("Sorry, you are not allowed to access this document."))

                if self.env.user.has_group('bi_payment_double_approval.group_payment_first_approval') and \
                    self.env.user.has_group('account.group_account_manager'):
                    payment.write({'state': 'first_approve'})
            # Second Approval
            elif payment.account_second_approval and not payment.account_first_approval:
                # Payment Second Approval AND Not Billing Manager
                if self.env.user.has_group('bi_payment_double_approval.group_payment_second_approval') and \
                    not self.env.user.has_group('account.group_account_manager'):
                    raise AccessError(_("Sorry, you are not allowed to access this document."))
                # Not Payment Second Approval AND Not Billing Manager
                elif not self.env.user.has_group('bi_payment_double_approval.group_payment_second_approval') and \
                    not self.env.user.has_group('account.group_account_manager'):
                    raise AccessError(_("Sorry, you are not allowed to access this document."))
                else:
                    # Not Payment Second Approval AND Billing Manager
                    if not self.env.user.has_group('bi_payment_double_approval.group_payment_second_approval') and \
                        self.env.user.has_group('account.group_account_manager'):
                        raise AccessError(_("Sorry, you are not allowed to access this document."))

                if self.env.user.has_group('bi_payment_double_approval.group_payment_second_approval') and \
                    self.env.user.has_group('account.group_account_manager'):
                    payment.write({'state': 'first_approve'})
            else : 
                return super(AccountPayment, self).action_post()
            return True



    def button_second_approve(self):
        for payment in self:
            if payment.account_second_approval:
                # payment.write({'state': 'second_approve'})
                return super(AccountPayment, self).action_post()
            else : 
                return super(AccountPayment, self).action_post()
            return True

    
    # def button_payment_post_second(self):
    #     for rec in self:
    #         rec.write({'state':'posted'})

    
    def button_payment_post_first(self):
        for rec in self:
            res_config = self.env['res.config.settings'].sudo().search([], order="id desc", limit=1)
            if res_config.account_first_approval and res_config.account_second_approval and rec.amount >= res_config.account_second_approval_minimum_amount :
                rec.write({'state': 'second_approve'})
            elif  res_config.account_first_approval:
                if not self.env.user.has_group('bi_payment_double_approval.group_payment_first_approval'):
                    raise AccessError(_("Sorry, you are not have access right of approve payment"))
                else:
                    rec.write({'state':'posted'})

    def action_validate_invoice_payment(self):
        """ Posts a payment used to pay an invoice. This function only posts the
        payment by default but can be overridden to apply specific post or pre-processing.
        It is called by the "validate" button of the popup window
        triggered on invoice form by the "Register Payment" button.
        """
        if any(len(record.move_id) != 1 for record in self):
            # For multiple invoices, there is account.register.payments wizard
            raise UserError(_("This method should only be called to process a single invoice's payment."))
        return self.action_post()

    
    def unlink(self):
        for rec in self:
            if rec.state not in ('draft', 'cancel'):
                raise UserError(_('You cannot delete an payment which is not draft or cancelled.'))
        if any(bool(rec.move_line_ids) for rec in self):
            raise UserError(_("You cannot delete a payment that is already posted."))
        if any(rec.move_name for rec in self):
            raise UserError(_('It is not allowed to delete a payment that already created a journal entry since it would create a gap in the numbering. You should create the journal entry again and cancel it thanks to a regular revert.'))
        return super(AccountPayment, self).unlink()
