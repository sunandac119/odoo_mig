from odoo import api, fields, models, _
import xmlrpc.client
import socket
import requests


class PosSession(models.Model):
    _inherit = 'pos.session'

    @api.model
    def create(self, values):
        old_name = values.get('name')
        if values.get('config_id'):
            current_config_id = self.env['pos.config'].browse(values.get('config_id'))
            values.update({'name': "/" + current_config_id.name})
        res = super().create(values)
        if self.env.company.current_running_db_server == 'remote_server' and old_name:
            res.name = old_name
        return res

    def action_pos_session_closing_control_remote_server(self):
        if self.env.company.current_running_db_server == 'remote_server':
            self.action_pos_session_closing_control()
            self._compute_cash_balance()
            # self.stop_at =
            print("Hiieas")
            return True

    def remote_session_cash_difference_entrys_postings(self, cash_difference_amount, cash_register_balance_start):
        if self.env.company.current_running_db_server == 'remote_server':
            # print("Hiieas")
            self.state == 'opened'
            # self.cash_register_balance_end = cash_register_balance_end
            cash_out_name = self.env['ir.sequence'].next_by_code('cash.box.out')
            cash_out_records_ids = self.env['cash.box.out'].sudo().create({
                'name': cash_out_name,
                'amount': cash_difference_amount
            })
            bank_statements = self.cash_register_id
            bank_statements.balance_start = cash_register_balance_start
            if bank_statements:
                cash_out_records_ids._run(bank_statements)
                self._compute_cash_balance()
            print("Hiieas")
        return True

    def action_custom_pos_session_validate(self):
        self.action_pos_session_validate()
        return True

    @api.depends('order_ids')
    def compute_to_check_session_is_synced(self):
        for session_id in self:
            session_is_synced = True
            for order in session_id.order_ids:
                if not order.is_synced_with_server:
                    session_is_synced = False
                    break
            session_id.is_synced_with_server = session_is_synced

    def is_internet_available(self):
        try:
            # Try to connect to Google's DNS server
            socket.create_connection(("8.8.8.8", 53))
            return True
        except OSError:
            return False

    def is_server_accessible(self, url):
        try:
            response = requests.get(url, timeout=5)  # Timeout after 5 seconds
            return response.status_code == 200
        except requests.ConnectionError:
            return False

    def pos_data_send_to_the_server(self):
        current_running_db_server = self.env.company.current_running_db_server
        remote_server_url = self.env.company.remote_server_url
        remote_server_db = self.env.company.remote_server_db
        remote_server_admin_user_name = self.env.company.remote_server_admin_user_name
        remote_server_admin_user_password = self.env.company.remote_server_admin_user_password

        # XML-RPC endpoints
        common_url = f"{remote_server_url}/xmlrpc/2/common"
        object_url = f"{remote_server_url}/xmlrpc/object"

        # Connect to Odoo using XML-RPC
        common = xmlrpc.client.ServerProxy(common_url)
        uid = common.authenticate(remote_server_db, remote_server_admin_user_name, remote_server_admin_user_password,
                                  {})
        models = xmlrpc.client.ServerProxy(object_url)

        if current_running_db_server == 'local_server' and self.is_internet_available() and self.is_server_accessible(
                remote_server_url):

            sessions_ids = self.env['pos.session'].search([('is_synced_with_server', '!=', True)], order="id asc")
            for session_id in sessions_ids:
                remote_session_db_id = session_id.remote_server_db_id
                if not remote_session_db_id:
                    new_sessions_data_dict = {
                        'user_id': session_id.user_id.id,
                        'config_id': session_id.config_id.id,
                        'start_at': session_id.start_at,
                        'name': session_id.name,
                        # 'cash_register_balance_start': session_id.cash_register_balance_start
                    }
                    if session_id.stop_at:
                        new_sessions_data_dict.update({'stop_at': session_id.stop_at})
                    # Create the pos.order record
                    remote_session_id = models.execute_kw(remote_server_db, uid, remote_server_admin_user_password,
                                                          'pos.session', 'create', [new_sessions_data_dict])
                    if remote_session_id:
                        session_id.remote_server_db_id = remote_session_id
                        remote_session_db_id = remote_session_id
                        # _synced_with_server = True

                for order in session_id.order_ids.filtered(lambda order: not order.is_synced_with_server):
                    # Prepare data for the new pos.order record
                    # self.send_pos_order_to_server()
                    pos_order_data = {
                        'partner_id': order.partner_id.remote_server_db_id or order.partner_id.id if order.partner_id else False,
                        'session_id': remote_session_db_id,
                        'date_order': order.date_order,
                        'name': order.name,
                        'user_id': order.user_id.remote_server_db_id or order.user_id.id,
                        'pos_reference': order.pos_reference,
                        'amount_tax': order.amount_tax,
                        'amount_total': order.amount_total,
                        'amount_paid': order.amount_paid,
                        'amount_return': order.amount_return,
                        'state': 'done',
                        'transaction_id': order.transaction_id,
                        'approval_code': order.approval_code,
                        'payment_terminal_inv_no': order.payment_terminal_inv_no,
                        'trace_no': order.trace_no,
                        'payments_terminal_id': order.payments_terminal_id,
                        'retrival_ref_no': order.retrival_ref_no,
                    }
                    orders_lines = []
                    for line in order.lines:
                        orders_lines.append(
                            (0, 0, {
                                'product_id': line.product_id.remote_server_db_id or line.product_id.id,
                                'qty': line.qty,
                                'price_unit': line.price_unit,
                                'price_subtotal': line.price_subtotal,
                                'price_subtotal_incl': line.price_subtotal_incl,
                            })
                        )
                    if orders_lines:
                        pos_order_data.update({'lines': orders_lines})

                        # Create the pos.order record
                        remote_order_id = models.execute_kw(remote_server_db, uid, remote_server_admin_user_password,
                                                            'pos.order', 'create', [pos_order_data])
                        if remote_order_id:
                            order.remote_server_db_id = remote_order_id
                            order.is_synced_with_server = True

                    if order.remote_server_db_id:
                        payments_lines = []
                        for pline in order.payment_ids.filtered(
                                lambda payment_id: not payment_id.is_synced_with_server):
                            payments_lines.append({
                                'name': pline.name,
                                'amount': pline.amount,
                                'pos_order_id': order.remote_server_db_id,
                                'payment_method_id': pline.payment_method_id.remote_server_db_id or pline.payment_method_id.id,
                                'session_id': order.session_id.remote_server_db_id
                            })
                        if payments_lines:
                            remote_payments_ids = models.execute_kw(remote_server_db, uid,
                                                                    remote_server_admin_user_password,
                                                                    'pos.payment', 'create', [payments_lines])
                            if remote_payments_ids:
                                for pline in order.payment_ids.filtered(
                                        lambda payment_id: not payment_id.is_synced_with_server):
                                    pline.is_synced_with_server = True
                if session_id.stop_at:
                    remote_server_order_picking_mapping_dict = {}
                    # cash_register_balance_start = session_id.cash_register_balance_start

                    # Cash Out Entrys managements
                    cash_payment_method = session_id.payment_method_ids.filtered('is_cash_count')[:1]
                    if cash_payment_method:
                        total_cash_payment = 0.0
                        result = self.env['pos.payment'].read_group(
                            [('session_id', '=', session_id.id), ('payment_method_id', '=', cash_payment_method.id)],
                            ['amount'], ['session_id'])
                        if result:
                            total_cash_payment = result[0]['amount']
                            cash_in = session_id.cash_register_balance_start
                            # start_balance = cash_in
                            # cash_register = session_id.cash_register_id
                            total_cash_payment += cash_in
                            if total_cash_payment:
                                cash_out_entry_amount = 0.0
                                if session_id.cash_real_difference == 0.0:
                                    # Total Cash Out
                                    cash_out_entry_amount = total_cash_payment
                                else:
                                    # Partials Cash Out
                                    cash_out_entry_amount = total_cash_payment + session_id.cash_real_difference
                                if cash_out_entry_amount:
                                    #             # Postings ans cash difference entryieas

                                    cash_register_balance_start = session_id.cash_register_balance_start
                                    x = models.execute_kw(remote_server_db, uid, remote_server_admin_user_password,
                                                          'pos.session',
                                                          'remote_session_cash_difference_entrys_postings',
                                                          [session_id.remote_server_db_id, -cash_out_entry_amount,
                                                           cash_register_balance_start])

                                    # Clossingeas ans remotes ans serveres created new sessions
                                    x = models.execute_kw(remote_server_db, uid, remote_server_admin_user_password,
                                                          'pos.session',
                                                          'action_pos_session_closing_control_remote_server',
                                                          [[session_id.remote_server_db_id]])

                    for order in session_id.order_ids:
                        remote_server_order_picking_mapping_dict.update({'origin': order.picking_ids.name})

                    y = models.execute_kw(remote_server_db, uid, remote_server_admin_user_password, 'pos.session',
                                          'action_custom_pos_session_validate', [[session_id.remote_server_db_id]])
                    # {'custom_param': remote_server_order_picking_mapping_dict})
                    session_id.is_synced_with_server = True
                    print("Hiieas")
