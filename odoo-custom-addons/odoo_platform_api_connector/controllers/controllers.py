# -*- coding: utf-8 -*-
from odoo import http
from odoo.http import request

INVOICE_TYPE_CODE = {
    "01": 'out_invoice',
    "02": 'out_refund',
    "11": 'in_invoice',
    "12": 'in_refund'

}


class AccountMoveAPI(http.Controller):

    @http.route('/odoo/api/create_account_move', type='json', auth='none', methods=['POST'], csrf=False)
    def create_account_move(self, **kwargs):
        # Extract parameters
        kwargs = request.httprequest.json
        admin_username = kwargs.get('username')
        admin_password = kwargs.get('password')
        move_data = kwargs.get('move_data')

        # Authenticate admin user
        if not self._authenticate_user(admin_username, admin_password):
            return {'status': 'error', 'message': 'Invalid credentials'}

        # Create account.move
        move_ids, already_created_move_ids_found, errors = self._create_account_move(move_data)

        if errors:
            return {'status': 'error', 'errors': errors}
        if move_ids or already_created_move_ids_found:
            return {'status': 'success', 'new_move_ids_in_api_server': move_ids,
                    'move_ids_already_available_in_api_server': already_created_move_ids_found}
        # if already_created_move_ids_found:
        #     return {'status': 'error',
        #             'errors': f'This Move already availables ins odoo ==>{already_created_move_ids_found}'}

    def _authenticate_user(self, username, password):
        # Logic to authenticate user
        # You might use request.env['res.users'].authenticate(username, password)
        user = request.env['res.users'].sudo().search([('login', '=', username)], limit=1)
        if user and request.session.authenticate(request.db, username, password):
            return True
        return False

    def _create_account_move(self, move_data):
        # Logic to create ans Account Move
        new_create_odoo_move_list = []
        already_created_account_move = []
        error = []
        for move in move_data:
            move_type = INVOICE_TYPE_CODE[move.get('document_type')]
            origin_uuid = ""
            if move_type in ['in_refund', 'out_refund']:
                origin_uuid = move.get('origin_uuid')
                if not origin_uuid:
                    error.append({'external_system_id': move.get('external_system_db_id'),
                                  'error_str': "partner ->This Documetns Required ans Origin UUID data because of ans Refund type documents"})
                    return [], [], error
            odoo_move_id_found = request.env['account.move'].sudo().search(
                [('external_system_db_id', '=', move.get('external_system_db_id'))])
            if not odoo_move_id_found:
                external_partner_obj = move.get('partner_id')
                odoo_partner_id = request.env['res.partner'].sudo().search(
                    [('external_system_db_id', '=', external_partner_obj.get('external_system_db_id'))])
                if not odoo_partner_id:
                    odoo_state_id = request.env['res.country.state'].sudo().search(
                        ['|', ('name', 'ilike', external_partner_obj.get('state')),
                         ('code', 'ilike', external_partner_obj.get('state'))], limit=1)
                    if not odoo_state_id:
                        error.append({'external_system_id': move.get('external_system_db_id'),
                                      'error_str': "partner ->State not found ins API server"})
                        return [], [], error

                    odoo_country_id = request.env['res.country'].sudo().search(
                        [('code', 'ilike', external_partner_obj.get('country_code'))], limit=1)
                    if not odoo_country_id:
                        error.append({'external_system_id': move.get('external_system_db_id'),
                                      'error_str': "partner ->Country not found ins API server"})
                        return [], [], error

                    odoo_msic_code_id = request.env['lhdn.msic.code'].sudo().search(
                        [('code', 'ilike', external_partner_obj.get('msic_code'))], limit=1)
                    if not odoo_msic_code_id:
                        error.append({'external_system_id': move.get('external_system_db_id'),
                                      'error_str': "partner ->MSIC Code not found ins API server"})
                        return [], [], error

                    odoo_partner_id = request.env['res.partner'].sudo().create({
                        'name': external_partner_obj.get('name'),
                        'external_system_db_id': external_partner_obj.get('external_system_db_id'),
                        'brn': external_partner_obj.get('business_registration_number'),
                        'msic_code_id': odoo_msic_code_id.id,
                        'tin': external_partner_obj.get('tax_identification_number'),
                        'street': external_partner_obj.get('street'),
                        'city': external_partner_obj.get('city'),
                        'zip': external_partner_obj.get('postal_code'),
                        'state_id': odoo_state_id.id,
                        'country_id': odoo_country_id.id,
                        'tin_status': 'validated'
                    })

                move_dict = {
                    'external_system_db_id': move.get('external_system_db_id'),
                    'external_system_invoice_number': move.get('external_system_invoice_number'),
                    'partner_id': odoo_partner_id.id,
                    'move_type': move_type,
                    'invoice_date': move.get('invoice_date')
                }

                external_currency_id = move.get('currency_id')
                odoo_currency_id_found = False
                if external_currency_id:
                    odoo_currency_id_found = request.env['res.currency'].sudo().search(
                        ['|', ('name', '=', external_currency_id), ('full_name', '=', external_currency_id)], limit=1)
                if odoo_currency_id_found:
                    move_dict.update({'currency_id': odoo_currency_id_found.id})

                if origin_uuid:
                    move_dict.update({'origin_lhdn_uuid': origin_uuid})
                lines = []
                for external_move_line in move.get('move_line'):
                    external_products_obj = external_move_line.get('product_id')

                    odoo_products_classification_id = request.env['lhdn.item.classification.code'].sudo().search(
                        [('code', '=', external_products_obj.get('classification_code'))], limit=1)
                    if not odoo_products_classification_id:
                        error.append({'external_system_id': move.get('external_system_db_id'),
                                      'error_str': f"Move Lines ->{external_products_obj.get('name')} -> classification_code not found ins API server"})
                        return [], [], error

                    odoo_product_id = request.env['product.product'].sudo().search(
                        [('external_system_db_id', '=', external_products_obj.get('external_system_db_id'))])
                    if not odoo_product_id:
                        odoo_product_id = request.env['product.product'].sudo().create({
                            'name': external_products_obj.get('name'),
                            'external_system_db_id': external_products_obj.get('external_system_db_id'),
                            'lhdn_classification_id': odoo_products_classification_id.id
                        })
                    discounts_in_pr = 0
                    if external_move_line.get('discount_amount'):
                        disc_amount = external_move_line.get('discount_amount')
                        total_amounts = external_move_line.get('quantity') * external_move_line.get('price_unit')
                        # discounts_in_pr = round( (disc_amount/total_amounts)*100, 3)
                        discounts_in_pr = (disc_amount / total_amounts) * 100
                        discounts_in_pr = discounts_in_pr
                    lines.append((0, 0, {
                        "product_id": odoo_product_id.id,
                        "display_type": 'product',
                        "account_id": 33,
                        "quantity": external_move_line.get('quantity'),
                        "price_unit": external_move_line.get('price_unit'),
                        "discount":discounts_in_pr
                    }))

                move_dict.update({'line_ids': lines})
                new_orders_id = request.env['account.move'].sudo().create(move_dict)
                new_create_odoo_move_list.append(new_orders_id.id)
            else:
                already_created_account_move.append(odoo_move_id_found.id)
        # return order.id if order else False
        return new_create_odoo_move_list, already_created_account_move, []

    # curl -X POST https://chainchon.my-einvoice.com/odoo/api/create_account_move \
    # -H "Content-Type: application/json" \
    # -d '{
    #     "username": "odoo",
    #     "password": "admin",
    #     "move_data": [
    #         {
    #             "external_system_db_id": 102,
    #             "external_system_invoice_number":"INV0001",
    #             "currency_id":"MYR",
    #             "document_type": "01", # Document Type (e.g., 01 for Tax Invoice)
    #             "uuid": "123e4567-e89b-12d3-a456-426614174000", # Reference original invoice UUID
    #             "partner_id": {
    #                 "external_system_db_id": 1,
    #                 "name": "XYZ",
    #                 "business_registration_number": "202001000123",
    #                 "msic_code": "62010",
    #                 "tax_identification_number": "1234567890",
    #                   "street": "123, Jalan Example",
    #                   "city": "Kuala Lumpur",
    #                   "postal_code": "50000",
    #                   "state": "Wilayah Persekutuan",
    #                   "country_code": "MY"

    #             },
    #             "invoice_date": "2024-10-30",
    #             "move_line": [
    #                 {
    #                     "product_id": {
    #                         "external_system_db_id": 1,
    #                         "name": "Prod-1",
    #                         "classification_code": "001",
    #                         "uom": "PCS"
    #                      },
    #                     "quantity": 100,
    #                     "price_unit": 20,
    #                     "discount_amount":25
    #                  }
    #             ]
    #         }
    #     ]
    # }'

    @http.route('/odoo/api/update_account_move', type='json', auth='none', methods=['POST'], csrf=False)
    def update_account_move(self, **kwargs):
        # Extract parameters
        kwargs = request.httprequest.json
        admin_username = kwargs.get('username')
        admin_password = kwargs.get('password')
        move_data = kwargs.get('update_data')

        # Authenticate admin user
        if not self._authenticate_user(admin_username, admin_password):
            return {'status': 'error', 'message': 'Invalid credentials'}

        # Create account.move
        updated_account_move, errors = self._update_account_move(move_data)

        if errors:
            return {'status': 'error', 'errors': errors}
        if updated_account_move:
            return {'status': 'success', 'account_move_updated_ids_in_api_server': updated_account_move}
        # if already_created_move_ids_found:
        #     return {'status': 'error',
        #             'errors': f'This Move already availables ins odoo ==>{already_created_move_ids_found}'}

    # def _authenticate_user(self, username, password):
    #     # Logic to authenticate user
    #     # You might use request.env['res.users'].authenticate(username, password)
    #     user = request.env['res.users'].sudo().search([('login', '=', username)], limit=1)
    #     if user and request.session.authenticate(request.db, username, password):
    #         return True
    #     return False

    def _update_account_move(self, move_data):
        # Logic to create ans Account Move
        # new_create_odoo_move_list = []
        updated_account_move = []
        error = []
        for move in move_data:
            move_type = INVOICE_TYPE_CODE[move.get('document_type')]
            origin_uuid = ""
            if move_type in ['in_refund', 'out_refund']:
                origin_uuid = move.get('origin_uuid')
                if not origin_uuid:
                    error.append({'external_system_id': move.get('external_system_db_id'),
                                  'error_str': "partner ->This Documetns Required ans Origin UUID data because of ans Refund type documents"})
                    return [], error
            odoo_move_id_found = request.env['account.move'].sudo().search(
                [('external_system_db_id', '=', move.get('external_system_db_id'))])
            if odoo_move_id_found:
                if odoo_move_id_found.state != 'draft':
                    error.append({'external_system_id': move.get('external_system_db_id'),
                                  'error_str': "partner ->This Documetns Can't update becase ins API server this document has state in posted"})
                    return [], error
                external_partner_obj = move.get('partner_id')
                odoo_partner_id = request.env['res.partner'].sudo().search(
                    [('external_system_db_id', '=', external_partner_obj.get('external_system_db_id'))])

                odoo_state_id = request.env['res.country.state'].sudo().search(
                    ['|', ('name', 'ilike', external_partner_obj.get('state')),
                     ('code', '=', external_partner_obj.get('state'))], limit=1)
                if not odoo_state_id:
                    error.append({'external_system_id': move.get('external_system_db_id'),
                                  'error_str': "partner ->State not found ins API server"})
                    return [], error

                odoo_country_id = request.env['res.country'].sudo().search(
                    [('code', 'ilike', external_partner_obj.get('country_code'))], limit=1)
                if not odoo_country_id:
                    error.append({'external_system_id': move.get('external_system_db_id'),
                                  'error_str': "partner ->Country not found ins API server"})
                    return [], error

                odoo_msic_code_id = request.env['lhdn.msic.code'].sudo().search(
                    [('code', 'ilike', external_partner_obj.get('msic_code'))], limit=1)
                if not odoo_msic_code_id:
                    error.append({'external_system_id': move.get('external_system_db_id'),
                                  'error_str': "partner ->MSIC Code not found ins API server"})
                    return [], error

                if not odoo_partner_id:
                    odoo_partner_id = request.env['res.partner'].sudo().create({
                        'name': external_partner_obj.get('name'),
                        'external_system_db_id': external_partner_obj.get('external_system_db_id'),
                        'brn': external_partner_obj.get('business_registration_number'),
                        'msic_code_id': odoo_msic_code_id.id,
                        'tin': external_partner_obj.get('tax_identification_number'),
                        'street': external_partner_obj.get('street'),
                        'city': external_partner_obj.get('city'),
                        'zip': external_partner_obj.get('postal_code'),
                        'state_id': odoo_state_id.id,
                        'country_id': odoo_country_id.id,
                        'tin_status': 'validated'
                    })
                else:
                    odoo_partner_id.sudo().write({
                        'name': external_partner_obj.get('name'),
                        'external_system_db_id': external_partner_obj.get('external_system_db_id'),
                        'brn': external_partner_obj.get('business_registration_number'),
                        'msic_code_id': odoo_msic_code_id.id,
                        'tin': external_partner_obj.get('tax_identification_number'),
                        'street': external_partner_obj.get('street'),
                        'city': external_partner_obj.get('city'),
                        'zip': external_partner_obj.get('postal_code'),
                        'state_id': odoo_state_id.id,
                        'country_id': odoo_country_id.id,
                        'tin_status': 'validated'
                    })
                move_dict = {
                    'external_system_db_id': move.get('external_system_db_id'),
                    'partner_id': odoo_partner_id.id,
                    'move_type': move_type,
                    'invoice_date': move.get('invoice_date')
                }

                external_currency_id = move.get('currency_id')
                odoo_currency_id_found = False
                if external_currency_id:
                    odoo_currency_id_found = request.env['res.currency'].sudo().search(
                        ['|', ('name', '=', external_currency_id), ('full_name', '=', external_currency_id)], limit=1)
                if odoo_currency_id_found:
                    move_dict.update({'currency_id': odoo_currency_id_found.id})

                if origin_uuid:
                    move_dict.update({'origin_lhdn_uuid': origin_uuid})
                lines = []
                for external_move_line in move.get('move_line'):
                    external_products_obj = external_move_line.get('product_id')

                    odoo_products_classification_id = request.env['lhdn.item.classification.code'].sudo().search(
                        [('code', '=', external_products_obj.get('classification_code'))], limit=1)
                    if not odoo_products_classification_id:
                        error.append({'external_system_id': move.get('external_system_db_id'),
                                      'error_str': "Move Lines ->Products -> classification_code not found ins API server"})
                        return [], error

                    odoo_product_id = request.env['product.product'].sudo().search(
                        [('external_system_db_id', '=', external_products_obj.get('external_system_db_id'))])
                    if not odoo_product_id:
                        odoo_product_id = request.env['product.product'].sudo().create({
                            'name': external_products_obj.get('name'),
                            'external_system_db_id': external_products_obj.get('external_system_db_id'),
                            'lhdn_classification_id': odoo_products_classification_id.id
                        })
                    else:
                        odoo_product_id.sudo().write({
                            'name': external_products_obj.get('name'),
                            'external_system_db_id': external_products_obj.get('external_system_db_id'),
                            'lhdn_classification_id': odoo_products_classification_id.id
                        })
                    existing_line_id = odoo_move_id_found.line_ids.filtered(
                        lambda line: line.product_id.id == odoo_product_id.id)

                    discounts_in_pr = 0
                    if external_move_line.get('discount_amount'):
                        disc_amount = external_move_line.get('discount_amount')
                        total_amounts = external_move_line.get('quantity') * external_move_line.get('price_unit')
                        # discounts_in_pr = round( (disc_amount/total_amounts)*100, 3)
                        discounts_in_pr = (disc_amount / total_amounts) * 100
                        discounts_in_pr = discounts_in_pr

                    if existing_line_id:
                        existing_line_id.quantity = external_move_line.get('quantity')
                        existing_line_id.price_unit = external_move_line.get('price_unit')
                        existing_line_id.discount = discounts_in_pr
                    else:
                        lines.append((0, 0, {
                            "product_id": odoo_product_id.id,
                            "display_type": 'product',
                            "account_id": 33,
                            "quantity": external_move_line.get('quantity'),
                            "price_unit": external_move_line.get('price_unit'),
                            "discount":discounts_in_pr
                        }))
                move_dict.update({'line_ids': lines})
                odoo_move_id_found.sudo().write(move_dict)
                updated_account_move.append(odoo_move_id_found.id)
            else:
                error.append({'external_system_id': move.get('external_system_db_id'),
                              'error_str': "partner ->This Documetns is nots founds ins API server first create the move"})
                # already_created_account_move.append(odoo_move_id_found.id)
                return [], error
        # return order.id if order else False
        return updated_account_move, []

    # curl -X POST https://chainchon.my-einvoice.com/odoo/api/update_account_move \
    # -H "Content-Type: application/json" \
    # -d '{
    #     "username": "odoo",
    #     "password": "admin",
    #     "update_data": [
    #         {
    #             "external_system_db_id": 102,
    #             "document_type": "01", # Document Type (e.g., 01 for Tax Invoice)
    #             "uuid": "123e4567-e89b-12d3-a456-426614174000", # Reference original invoice UUID
    #             "currency_id":"MYR",
    #             "partner_id": {
    #                 "external_system_db_id": 1,
    #                 "name": "XYZ",
    #                 "business_registration_number": "202001000123",
    #                 "msic_code": "62010",
    #                 "tax_identification_number": "1234567890",
    #                   "street": "123, Jalan Example",
    #                   "city": "Kuala Lumpur",
    #                   "postal_code": "50000",
    #                   "state": "Wilayah Persekutuan",
    #                   "country_code": "MY"

    #             },
    #             "invoice_date": "2024-10-30",
    #             "move_line": [
    #                 {
    #                     "product_id": {
    #                         "external_system_db_id": 1,
    #                         "name": "Prod-1",
    #                         "classification_code": "001",
    #                         "uom": "PCS"
    #                      },
    #                     "quantity": 100,
    #                     "price_unit": 20,
    #                     "discount_amount":25
    #                  }
    #             ]
    #         }
    #     ]
    # }'

    @http.route('/odoo/api/get/customer_info', type='json', auth='none', methods=['POST'], csrf=False)
    def get_customer_info(self, **kwargs):
        # Extract parameters
        kwargs = request.httprequest.json
        admin_username = kwargs.get('username')
        admin_password = kwargs.get('password')
        customer_ids = kwargs.get('external_system_db_ids')

        # Authenticate admin user
        if not self._authenticate_user(admin_username, admin_password):
            return {'status': 'error', 'message': 'Invalid credentials'}

        customer_info_list, not_found_customers_ids = self._get_customers_info(customer_ids)

        return {'status': 'success', 'customer_info': customer_info_list,
                'not_found_customers_ids_in_api_server': not_found_customers_ids}

    def _get_customers_info(self, customer_ids):
        customers_fields = ['external_system_db_id', 'name', 'phone', 'mobile', 'email', 'street', 'street2', 'zip',
                            'tin', 'brn', 'msic_code_id']
        customer_info_list = []
        not_found_customers_ids = []
        for id in customer_ids:
            odoo_customer_id_found = request.env['res.partner'].sudo().search_read(
                [('external_system_db_id', '=', id)], fields=customers_fields)
            if not odoo_customer_id_found:
                not_found_customers_ids.append(id)
            else:
                customer_info_list.append(odoo_customer_id_found[0])
        return customer_info_list, not_found_customers_ids

    # curl -X POST https://chainchon.my-einvoice.com/odoo/api/get/customer_info \
    # -H "Content-Type: application/json" \
    # -d '{
    #     "username": "odoo",
    #     "password": "admin",
    #     "external_system_db_ids": [10]
    # }'

    @http.route('/odoo/api/create_customer', type='json', auth='none', methods=['POST'], csrf=False)
    def create_customer(self, **kwargs):
        # Extract parameters
        kwargs = request.httprequest.json
        admin_username = kwargs.get('username')
        admin_password = kwargs.get('password')
        customers = kwargs.get('customers')

        # Authenticate admin user
        if not self._authenticate_user(admin_username, admin_password):
            return {'status': 'error', 'message': 'Invalid credentials'}

        new_customer_created, already_available_customers_ids, error = self._create_customer(customers)
        if error:
            return {'status': 'error', 'message': error}

        return {'status': 'success', 'new_customer_created_in_api_server': new_customer_created,
                'customer_already_available_in_api_server': already_available_customers_ids}

    def _create_customer(self, customers):
        customers_fields = ['name', 'phone', 'mobile', 'email', 'street', 'street2', 'zip',
                            'tin', 'brn']
        new_customer_created = []
        # not_updated_customers_ids = []
        already_available_customers_ids = []
        error = []
        for customer in customers:
            if customer.get('external_system_db_id'):
                odoo_customer_id_found = request.env['res.partner'].sudo().search(
                    [('external_system_db_id', '=', customer.get('external_system_db_id'))])
                # odoo_msic_code_id = False
                if customer.get('msic_code'):
                    odoo_msic_code_id = request.env['lhdn.msic.code'].sudo().search(
                        [('code', '=', customer.get('msic_code_id'))])
                    if odoo_msic_code_id:
                        customer.update({'msic_code_id': odoo_msic_code_id.id})
                    else:
                        customer.update({'msic_code_id':False})
                odoo_state_id = request.env['res.country.state'].sudo().search(
                    ['|', ('name', 'ilike', customer.get('state_id')),
                     ('code', 'ilike', customer.get('state_id'))], limit=1)
                if not odoo_state_id:
                    error.append({'external_system_id': customer.get('external_system_db_id'),
                                  'error_str': "partner's State not found ins API server"})
                    return [], [], error

                odoo_country_id = request.env['res.country'].sudo().search(
                    [('code', 'ilike', customer.get('country_id'))], limit=1)

                if not odoo_state_id:
                    error.append({'external_system_id': customer.get('external_system_db_id'),
                                  'error_str': "partner's Countrys not found ins API server"})
                    return [], [], error

                customer.update({
                    'state_id': odoo_state_id.id,
                    'country_id': odoo_country_id.id
                })
                if not odoo_customer_id_found:
                    odoo_partner_id = request.env['res.partner'].sudo().create(customer)
                    new_customer_created.append(odoo_partner_id.id)
                else:
                    already_available_customers_ids.append(customer.get('external_system_db_id'))
            else:
                print("Hiieas")
                # bad_record_data_provide.append(customer)
        return new_customer_created, already_available_customers_ids, error

    # curl -X POST https://chainchon.my-einvoice.com/odoo/api/create_customer \
    # -H "Content-Type: application/json" \
    # -d '{
    #     "username": "odoo",
    #     "password": "admin",
    #     "customers": [
    #         {
    #             "external_system_db_id":102,
    #             "name":"Test-name",
    #             "phone":"123456766",
    #             "mobile":"675464787",
    #             "email":"test@gmail.com",
    #             "street":"xyz",
    #             "street2":"abc",
    #             "zip":"4000001",
    #             "tin":"C134235452",
    #             "brn":"C134235452",
    #             "msic_code":"",
    #             "state":"",
    #             "country":"MY",

    #         },
    #         {
    #             "external_system_db_id": 103,
    #             "name":"Test-name2",
    #             "phone":"123456766",
    #             "mobile":"675464787",
    #         }
    #     ]
    # }'

    @http.route('/odoo/api/update/customer_info', type='json', auth='none', methods=['POST'], csrf=False)
    def update_customer_info(self, **kwargs):
        # Extract parameters
        kwargs = request.httprequest.json
        admin_username = kwargs.get('username')
        admin_password = kwargs.get('password')
        customers_info = kwargs.get('customers_info')

        # Authenticate admin user
        if not self._authenticate_user(admin_username, admin_password):
            return {'status': 'error', 'message': 'Invalid credentials'}

        customer_info_updated, not_updated_customers_ids, bad_record_data_provide = self._update_customer_info(
            customers_info)

        return {'status': 'success', 'customer_info_successfully_updated_in_api_server': customer_info_updated,
                'not_updated_customers_ids_in_api_server': not_updated_customers_ids,
                'bad_record_data_provide_in_api_server': bad_record_data_provide}

    def _update_customer_info(self, customers_info):
        customers_fields = ['name', 'phone', 'mobile', 'email', 'street', 'street2', 'zip',
                            'tin', 'brn']
        customer_info_updated = []
        not_updated_customers_ids = []
        bad_record_data_provide = []
        for customer in customers_info:

            if customer.get('external_system_db_id'):
                odoo_customer_id_found = request.env['res.partner'].sudo().search(
                    [('external_system_db_id', '=', customer.get('external_system_db_id'))])
                odoo_msic_code_id = False
                if customer.get('msic_code'):
                    odoo_msic_code_id = request.env['lhdn.msic.code'].sudo().search(
                        [('code', '=', customer.get('msic_code'))])
                if not odoo_customer_id_found:
                    not_updated_customers_ids.append(customer.get('external_system_db_id'))
                else:
                    odoo_rec_dict = {}
                    for field in customers_fields:
                        odoo_rec_dict.update({field: customer.get(field)})
                    if odoo_msic_code_id:
                        odoo_rec_dict.update({'msic_code_id': odoo_msic_code_id.id})
                    if odoo_rec_dict:
                        odoo_customer_id_found.sudo().write(odoo_rec_dict)
                    customer_info_updated.append(customer.get('external_system_db_id'))
            else:
                bad_record_data_provide.append(customer)
        return customer_info_updated, not_updated_customers_ids, bad_record_data_provide

    # curl -X POST https://chainchon.my-einvoice.com/odoo/api/update/customer_info \
    # -H "Content-Type: application/json" \
    # -d '{
    #     "username": "odoo",
    #     "password": "admin",
    #     "customers_info": [
    #         {
    #             "external_system_db_id":102,
    #             "name":"Test-name",
    #             "phone":"123456766",
    #             "mobile":"675464787",
    #             "email":"test@gmail.com",
    #             "street":"xyz",
    #             "street2":"abc",
    #             "zip":"4000001",
    #             "tin":"C134235452",
    #             "brn":"C134235452",
    #               "msic_code":"",
    #         },
    #         {
    #             "external_system_db_id": 103,
    #             "name":"Test-name2",
    #             "phone":"123456766",
    #             "mobile":"675464787",
    #         }
    #     ]
    # }'

    @http.route('/odoo/api/get/lhdn_invoice_status', type='json', auth='none', methods=['POST'], csrf=False)
    def get_lhdn_invoice_status(self, **kwargs):
        # Extract parameters
        kwargs = request.httprequest.json
        admin_username = kwargs.get('username')
        admin_password = kwargs.get('password')
        invoice_ids = kwargs.get('external_system_invoice_ids')

        # Authenticate admin user
        if not self._authenticate_user(admin_username, admin_password):
            return {'status': 'error', 'message': 'Invalid credentials'}

        invoice_status_found, invoice_not_found = self._get_lhdn_invoice_status(invoice_ids)

        return {'status': 'success', 'invoice_lhdn_status_found': invoice_status_found,
                'invoice_not_found': invoice_not_found}

    def _get_lhdn_invoice_status(self, invoice_ids):
        # customers_fields = ['external_system_db_id', 'name', 'phone', 'mobile', 'email', 'street', 'street2', 'zip',
        #                     'tin', 'brn']
        invoice_status_found = []
        invoice_not_found = []
        for id in invoice_ids:
            odoo_invoice_id_found = request.env['account.move'].sudo().search(
                [('external_system_db_id', '=', id)],limit=1)
            if not odoo_invoice_id_found:
                invoice_not_found.append(id)
            else:
                if odoo_invoice_id_found.lhdn_invoice_status == "submitted":
                    odoo_invoice_id_found.get_lhdn_documents_status()
                invoice_status_found.append({id: odoo_invoice_id_found.lhdn_invoice_status})
        return invoice_status_found, invoice_not_found

    # curl -X POST https://chainchon.my-einvoice.com/odoo/api/get/lhdn_invoice_status \
    # -H "Content-Type: application/json" \
    # -d '{
    #     "username": "odoo",
    #     "password": "admin",
    #     "external_system_invoice_ids":[123,1234,324]
    # }'

    @http.route('/odoo/api/get/lhdn_invoice_longid_uuid', type='json', auth='none', methods=['POST'], csrf=False)
    def get_lhdn_invoice_longid_uuid(self, **kwargs):
        # Extract parameters
        kwargs = request.httprequest.json
        admin_username = kwargs.get('username')
        admin_password = kwargs.get('password')
        invoice_ids = kwargs.get('external_system_invoice_ids')

        # Authenticate admin user
        if not self._authenticate_user(admin_username, admin_password):
            return {'status': 'error', 'message': 'Invalid credentials'}

        invoice_id_not_found, invoice_found_with_longid_uuid, invoice_not_lhdn_submitted = self._get_lhdn_invoice_longid_uuid(
            invoice_ids)

        return {'status': 'success', 'invoice_id_not_found_ins_api_server': invoice_id_not_found,
                'invoice_found_with_longid_uuid': invoice_found_with_longid_uuid,
                'invoice_not_lhdn_submitted': invoice_not_lhdn_submitted}

    def _get_lhdn_invoice_longid_uuid(self, invoice_ids):
        # customers_fields = ['external_system_db_id', 'name', 'phone', 'mobile', 'email', 'street', 'street2', 'zip',
        #                     'tin', 'brn']
        invoice_id_not_found = []
        invoice_found_with_longid_uuid = []
        invoice_not_lhdn_submitted = []
        for id in invoice_ids:
            odoo_invoice_id_found = request.env['account.move'].sudo().search(
                [('external_system_db_id', '=', id)],limit=1)
            if not odoo_invoice_id_found:
                invoice_id_not_found.append(id)
            else:
                if not odoo_invoice_id_found.lhdn_uuid:
                    invoice_not_lhdn_submitted.append(id)
                else:
                    invoice_found_with_longid_uuid.append({id: {
                        "uuid": odoo_invoice_id_found.lhdn_uuid,
                        "longid": odoo_invoice_id_found.lhdn_longid}})
        return invoice_id_not_found, invoice_found_with_longid_uuid, invoice_not_lhdn_submitted

    # curl -X POST https://chainchon.my-einvoice.com/odoo/api/get/lhdn_invoice_longid_uuid \
    # -H "Content-Type: application/json" \
    # -d '{
    #     "username": "odoo",
    #     "password": "admin",
    #     "external_system_invoice_ids":[123,1234,324]
    # }'

    @http.route('/odoo/api/lhdn/submit_or_resubmit_invoice', type='json', auth='none', methods=['POST'], csrf=False)
    def lhdn_submit_or_resubmit_invoice(self, **kwargs):
        # Extract parameters
        kwargs = request.httprequest.json
        admin_username = kwargs.get('username')
        admin_password = kwargs.get('password')
        invoice_id = kwargs.get('external_system_invoice_db_id')

        # Authenticate admin user
        if not self._authenticate_user(admin_username, admin_password):
            return {'status': 'error', 'message': 'Invalid credentials'}

        invoice_id_not_found, invoice_already_lhdn_submitted, invoice_not_lhdn_submitted = self._lhdn_submit_or_resubmit_invoice(
            invoice_id)

        return {'status': 'success',
                'message': "LHDN Documents request submitted,You need to check the Documents status usings ==> /odoo/api/get/lhdn_invoice_status thi API"}

    def _lhdn_submit_or_resubmit_invoice(self, invoice_id):
        # customers_fields = ['external_system_db_id', 'name', 'phone', 'mobile', 'email', 'street', 'street2', 'zip',
        #                     'tin', 'brn']
        invoice_id_not_found = []
        invoice_already_lhdn_submitted = []
        invoice_not_lhdn_submitted = []
        # for id in invoice_ids:
        odoo_invoice_id_found = request.env['account.move'].sudo().search(
            [('external_system_db_id', '=', invoice_id)],limit=1)
        if not odoo_invoice_id_found:
            invoice_id_not_found.append(id)
        else:
            if odoo_invoice_id_found.lhdn_invoice_status == 'validated':
                invoice_already_lhdn_submitted.append(id)
            else:
                x = odoo_invoice_id_found.e_invoice_validate()
                # invoice_found_with_longid_uuid.append({id: {
                #     "uuid": odoo_invoice_id_found.lhdn_uuid,
                #     "longid": odoo_invoice_id_found.lhdn_longid}})
                print(x)
        return invoice_id_not_found, invoice_already_lhdn_submitted, invoice_not_lhdn_submitted

    #
    # curl -X POST http://127.0.0.1:8078/odoo/api/lhdn/submit_or_resubmit_invoice \
    # -H "Content-Type: application/json" \
    # -d '{
    #     "username": "odoo",
    #     "password": "admin",
    #     "external_system_invoice_db_id":110
    # }'

    @http.route('/odoo/api/create_sale_order', type='json', auth='none', methods=['POST'], csrf=False)
    def create_sale_order(self, **kwargs):
        # Extract parameters
        kwargs = request.httprequest.json
        admin_username = kwargs.get('username')
        admin_password = kwargs.get('password')
        order_data = kwargs.get('order_data')

        # Authenticate admin user
        if not self._authenticate_user(admin_username, admin_password):
            return {'status': 'error', 'message': 'Invalid credentials'}

        # Create sale order
        new_create_odoo_orders_list, already_available_sale_orders, error = self._create_sale_order(order_data)

        if error:
            return {'status': 'error', 'message': error}
        else:
            return {'status': 'success', 'new_sale_order_created_in_api_server': new_create_odoo_orders_list,
                    'sale_order_already_available_ins_api_server': already_available_sale_orders}

    def _create_sale_order(self, order_data):
        # Logic to create a sale order
        new_create_odoo_orders_list = []
        already_available_sale_orders = []
        error = []
        for order in order_data:
            odoo_order_id_found = request.env['sale.order'].sudo().search(
                [('external_system_db_id', '=', order.get('external_system_db_id'))])
            if not odoo_order_id_found:
                ap_partner_obj = order.get('partner_id')
                odoo_partner_id = request.env['res.partner'].sudo().search(
                    [('external_system_db_id', '=', ap_partner_obj.get('external_system_db_id'))])
                if not odoo_partner_id:
                    odoo_state_id = request.env['res.country.state'].sudo().search(
                        ['|', ('name', 'ilike', ap_partner_obj.get('state')),
                         ('code', 'ilike', ap_partner_obj.get('state'))], limit=1)
                    if not odoo_state_id:
                        error.append({'external_system_id': order.get('external_system_db_id'),
                                      'error_str': "partner ->State not found ins API server"})
                        return [], [], error

                    odoo_country_id = request.env['res.country'].sudo().search(
                        [('code', 'ilike', ap_partner_obj.get('country_code'))], limit=1)
                    if not odoo_country_id:
                        error.append({'external_system_id': order.get('external_system_db_id'),
                                      'error_str': "partner ->Country not found ins API server"})
                        return [], [], error

                    odoo_msic_code_id = request.env['lhdn.msic.code'].sudo().search(
                        [('code', 'ilike', ap_partner_obj.get('msic_code'))], limit=1)
                    if not odoo_msic_code_id:
                        error.append({'external_system_id': order.get('external_system_db_id'),
                                      'error_str': "partner ->MSIC Code not found ins API server"})
                        return [], [], error

                    odoo_partner_id = request.env['res.partner'].sudo().create({
                        'name': ap_partner_obj.get('name'),
                        'phone': ap_partner_obj.get('phone'),
                        'email': ap_partner_obj.get('email'),
                        'external_system_db_id': ap_partner_obj.get('external_system_db_id'),
                        'brn': ap_partner_obj.get('business_registration_number'),
                        'msic_code_id': odoo_msic_code_id.id,
                        'tin': ap_partner_obj.get('tax_identification_number'),
                        'street': ap_partner_obj.get('street'),
                        'city': ap_partner_obj.get('city'),
                        'zip': ap_partner_obj.get('postal_code'),
                        'state_id': odoo_state_id.id,
                        'country_id': odoo_country_id.id,
                        'tin_status': 'validated'
                    })
                order_dict = {
                    'external_system_db_id': order.get('external_system_db_id'),
                    'partner_id': odoo_partner_id.id,
                    'date_order': order.get('date_order')
                }

                external_currency_id = order.get('currency_id')
                odoo_currency_id_found = False
                if external_currency_id:
                    odoo_currency_id_found = request.env['res.currency'].sudo().search(
                        ['|', ('name', '=', external_currency_id), ('full_name', '=', external_currency_id)], limit=1)
                if odoo_currency_id_found:
                    order_dict.update({'currency_id': odoo_currency_id_found.id})
                lines = []
                for ap_line in order.get('order_line'):
                    ap_products_obj = ap_line.get('product_id')
                    odoo_product_id = request.env['product.product'].sudo().search(
                        [('external_system_db_id', '=', ap_products_obj.get('external_system_db_id'))])

                    odoo_products_classification_id = request.env['lhdn.item.classification.code'].sudo().search(
                        [('code', '=', ap_products_obj.get('classification_code'))], limit=1)
                    if not odoo_products_classification_id:
                        error.append({'external_system_id': order.get('external_system_db_id'),
                                      'error_str': f"Move Lines ->{ap_products_obj.get('name')} -> classification_code not found ins API server"})
                        return [], [], error

                    if not odoo_product_id:
                        odoo_product_id = request.env['product.product'].sudo().create({
                            'name': ap_products_obj.get('name'),
                            'external_system_db_id': ap_products_obj.get('external_system_db_id'),
                            'lhdn_classification_id': odoo_products_classification_id.id
                        })

                    # if ap_line.get('discount_percentage') and ap_line.get('discount_amount'):
                    #     error.append({'external_system_id': order.get('external_system_db_id'),
                    #                   'error_str': f"Move Lines ->{ap_products_obj.get('name')} -> You can't gives the discount_percentage and discount_amount at a time. Need to use any one"})
                    #     return [], [], error
                    discounts_in_pr = 0
                    if ap_line.get('discount_amount'):
                        disc_amount = ap_line.get('discount_amount')
                        total_amounts = ap_line.get('product_uom_qty') * ap_line.get('price_unit')
                        # discounts_in_pr = round( (disc_amount/total_amounts)*100, 3)
                        discounts_in_pr = (disc_amount / total_amounts) * 100
                        discounts_in_pr = discounts_in_pr
                    lines.append((0, 0, {
                        "product_id": odoo_product_id.id,
                        "product_uom_qty": ap_line.get('product_uom_qty'),
                        "price_unit": ap_line.get('price_unit'),
                        'discount':discounts_in_pr
                    }))
                order_dict.update({'order_line': lines})
                new_orders_id = request.env['sale.order'].sudo().create(order_dict)
                new_create_odoo_orders_list.append(new_orders_id.id)
            else:
                already_available_sale_orders.append(odoo_order_id_found.id)
        # return order.id if order else False
        return new_create_odoo_orders_list, already_available_sale_orders, error

    # curl -X POST https://photobook.my-einvoice.com/odoo/api/create_sale_order \
    # -H "Content-Type: application/json" \
    # -d '{
    #     "username": "odoo",
    #     "password": "admin",
    #     "order_data": [
    #         {
    #             "external_system_db_id": 102,
    #             "currency_id":"MYR",
    #             "partner_id": {
    #                 "external_system_db_id": 1,
    #                 "name": "XYZ",
    #                 "phone": "+601232143",
    #                 "email": "test@gmail.com",
    #                 "business_registration_number": "202001000123",
    #                 "msic_code": "62010",
    #                 "tax_identification_number": "1234567890",
    #                 "street": "123, Jalan Example",
    #                 "city": "Kuala Lumpur",
    #                 "postal_code": "50000",
    #                 "state": "Wilayah Persekutuan",
    #                 "country_code": "MY"
    #             },
    #             "date_order": "2024-10-30 21:07:02",
    #             "order_line": [
    #                 {
    #                     "product_id": {
    #                         "external_system_db_id": 1,
    #                         "name": "Prod-1",
    #                         "classification_code": "001",
    #                         "uom": "PCS"
    #                     },
    #                     "product_uom_qty": 100,
    #                     "price_unit": 20,
    #                     "discount_amount":25
    #                 }
    #             ]
    #         }
    #     ]
    # }'



    @http.route('/odoo/api/get/account_move_status', type='json', auth='none', methods=['POST'], csrf=False)
    def get_account_move_status(self, **kwargs):
        # Extract parameters
        kwargs = request.httprequest.json
        admin_username = kwargs.get('username')
        admin_password = kwargs.get('password')
        invoice_ids = kwargs.get('external_system_invoice_ids')

        # Authenticate admin user
        if not self._authenticate_user(admin_username, admin_password):
            return {'status': 'error', 'message': 'Invalid credentials'}

        account_move_status_found, account_move_not_found = self._get_account_move_status(invoice_ids)

        return {'status': 'success', 'account_move_status_found': account_move_status_found,
                'account_move_not_found': account_move_not_found}

    def _get_account_move_status(self, invoice_ids):
        # customers_fields = ['external_system_db_id', 'name', 'phone', 'mobile', 'email', 'street', 'street2', 'zip',
        #                     'tin', 'brn']
        account_move_status_found = []
        account_move_not_found = []
        for id in invoice_ids:
            odoo_invoice_id_found = request.env['account.move'].sudo().search(
                ['|',('external_system_db_id', '=', id),('external_system_invoice_number', '=', id)],limit=1)
            if not odoo_invoice_id_found:
                account_move_not_found.append(id)
            else:
                account_move_status_found.append({id: odoo_invoice_id_found.state})
        return account_move_status_found, account_move_not_found

    # curl -X POST https://chainchon.my-einvoice.com/odoo/api/get/account_move_status \
    # -H "Content-Type: application/json" \
    # -d '{
    #     "username": "odoo",
    #     "password": "admin",
    #     "external_system_invoice_ids":[123,1234,324]
    # }'
