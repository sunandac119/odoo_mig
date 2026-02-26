# -*- coding: utf-8 -*-
from odoo import http
from odoo.addons.point_of_sale.controllers.main import PosController
from odoo.http import request
import xmlrpc.client
import socket
import requests
from datetime import datetime
import logging
import copy
# Define batch size to avoid memory overload
BATCH_SIZE = 100  # Adjust as needed based on your system's memory
# # XML-RPC endpoints
# common_url = f"{remote_server_url}/xmlrpc/2/common"
# object_url = f"{remote_server_url}/xmlrpc/object"

_logger = logging.getLogger("Odoo Pos Offlines Mode ==>")
# 'product.removal': ['id', 'name', 'method'],
FIELDS = {'account.tax.group': ['id', 'name'],
          'account.tax': ['id', 'name', 'amount_type', 'type_tax_use', 'tax_scope', 'amount', 'description',
                          'price_include', 'include_base_amount'],

          'product.category': ['id', 'name', 'parent_id', 'property_cost_method', 'property_valuation'],
          'product.attribute': ['id', 'name', 'display_type', 'create_variant'],
          'product.attribute.value': ['id', 'name', 'sequence', 'attribute_id', 'is_custom', 'html_color'],
          'product.template.attribute.value': ['id', 'attribute_id', 'name', 'display_type', 'price_extra'],
          'pos.category': ['id', 'name', 'parent_id', 'sequence'],
          'stock.location': ['id', 'name', 'location_id', 'usage', 'scrap_location', 'return_location'],
          'stock.warehouse': ['id', 'name', 'code', 'partner_id', 'lot_stock_id'],

          'ir.sequence': [],
          'stock.picking.type': ['id', 'name', 'sequence', 'sequence_id', 'sequence_code', 'warehouse_id',
                                 'default_location_src_id',
                                 'default_location_dest_id', 'code', 'return_picking_type_id',
                                 'use_create_lots', 'use_existing_lots', 'show_operations',
                                 'show_reserved', 'company_id'],

          'account.payment.method': ['id', 'name', 'code', 'payment_type', 'sequence'],
          'account.journal': ['id', 'name', 'type', 'inbound_payment_method_ids', 'outbound_payment_method_ids'],
          'pos.payment.method': ['id', 'name', 'is_cash_count', 'cash_journal_id', 'split_transactions'],

          'res.partner.industry': ['id', 'name', 'full_name'],
          'account.fiscal.position': ['id', 'name', 'auto_apply', ''],
          'account.fiscal.position.tax': ['id', 'name', 'tax_src_id', 'tax_dest_id', 'position_id'],
          'account.payment.term': ['id', 'name', 'note'],
          'account.payment.term.line': ['id', 'value', 'value_amount', 'days', 'option', 'day_of_the_month',
                                        'payment_id', 'sequence'],
          'res.users': ['id', 'name', 'partner_id','login','password'],
          'crm.team': ['id', 'name', 'use_quotations', 'user_id',
                       'invoiced_target', 'member_ids'],
          'res.partner.category': ['id', 'name'],

          'res.bank': ['id', 'name', 'bic', 'street', 'street2', 'city', 'state', 'zip', 'country', 'phone', 'email'],
          'res.partner.bank': ['acc_holder_name', 'acc_number', 'acc_type', 'bank_bic', 'bank_id', 'bank_name',
                               'partner_id', 'sanitized_acc_number', 'sequence'],

          'product.pricelist': ['id', 'name', 'country_group_ids'],
          'product.pricelist.item': ['id', 'name', 'applied_on', 'base', 'base_pricelist_id', 'categ_id',
                                     'compute_price', 'date_end', 'date_start', 'fixed_price', 'min_quantity',
                                     'percent_price', 'price', 'price_discount', 'price_max_margin', 'price_min_margin',
                                     'price_round', 'pricelist_id', 'product_id', 'product_tmpl_id'],
          'uom.category': ['id', 'name', 'is_pos_groupable'],
          'uom.uom': ['name', 'category_id', 'factor', 'factor_inv', 'rounding', 'uom_type', 'is_pos_groupable', 'id',
                      'display_name'],
         # 'user_ids',, 'title'
          'res.partner': ['id', 'name', 'date', 'parent_id', 'parent_name', 'child_ids', 'ref',
                          'vat', 'same_vat_partner_id', 'bank_ids', 'comment',
                          'category_id', 'credit_limit', 'employee', 'function', 'type',
                          'street', 'street2', 'zip', 'city', 'state_id', 'country_id', 'partner_latitude',
                          'partner_longitude', 'email', 'mobile', 'is_company', 'industry_id', 'company_type',
                          'team_id',
                          'barcode', 'property_payment_term_id', 'property_supplier_payment_term_id',
                          'property_account_position_id', 'property_stock_customer', 'property_stock_supplier',
                          'email', 'phone', 'user_id',
                          'credit',
                          'debit', 'debit_limit', 'currency_id',
                          'image_1920',
                          'image_1024', 'image_512', 'image_256', 'image_128',
                          'is_blacklisted'],
          # foreas aneas proddutc.producteas ==> 'price_extra', 'code','partner_ref','product_template_attribute_value_ids''combination_indices','image_variant_1024','stock_quant_ids', 'free_qty','qty_available', 'virtual_available', 'incoming_qty', 'outgoing_qty','orderpoint_ids,'value_svl','quantity_svl', 'stock_valuation_layer_ids',, 'activity_ids'
          #, 'template_multi_barcodes','multi_barcode_ids'
          'product.template': ['name', 'price', 'lst_price', 'default_code', 'type',
                               'barcode', 'description', 'description_sale',
                               'available_in_pos', 'pos_categ_id', 'description_pickingout', 'description_pickingin',
                               'description_picking', 'responsible_id',
                               'is_product_variant', 'standard_price', 'volume', 'weight',
                               'pricelist_item_count', 'image_1920', 'image_1024', 'image_512', 'image_256',
                               'image_128', 'can_image_1024_be_zoomed',
                               'nbr_reordering_rules', 'reordering_min_qty', 'reordering_max_qty',
                               'valuation',
                               'cost_method', 'id', 'display_name', 'categ_id'],
          'multi.barcode.products': ['id', 'multi_barcode', 'template_multi'],
          'product.multi.barcode': ['id', 'multi_barcode', 'product_tmpl_id'],
          'hr.department': ['id', 'name', 'parent_id'],
          'hr.employee': ['id', 'name', 'job_title', 'mobile_phone', 'work_phone', 'work_email', 'parent_id',
                          'pin', 'barcode', 'user_id']  # 'department_id','coach_id', 'job_id'
          }


class PosControllerPosOffline(PosController):

    def is_internet_available(self):
        try:
            # Try to connect to Google's DNS server
            socket.create_connection(("8.8.8.8", 53))
            return True
        except OSError:
            _logger.info("Remote Database is not accessible may be the internet issues")
            return False

    def is_server_accessible(self, url):
        try:
            response = requests.get(url, timeout=5)  # Timeout after 5 seconds
            return response.status_code == 200
        except requests.ConnectionError:
            _logger.info(
                f"Remote servers url {url} ==> is now not accessible may be the internet issues or may be the url issueas")
            return False

    def get_model_fields(self, model):
        pop_list = ['is_synced_with_server', 'remote_server_db_id', 'id', 'display_name', 'create_uid', 'create_date',
                    'write_uid', 'write_date', '__last_update', 'activity_state', 'activity_user_id',
                    'activity_type_id', 'activity_type_icon', 'activity_date_deadline', 'my_activity_date_deadline',
                    'activity_summary', 'activity_exception_decoration', 'activity_exception_icon',
                    'message_is_follower', 'message_follower_ids', 'message_partner_ids', 'message_channel_ids',
                    'message_ids', 'message_unread', 'message_unread_counter', 'message_needaction',
                    'message_needaction_counter', 'message_has_error', 'message_has_error_counter',
                    'message_attachment_count', 'message_main_attachment_id', 'website_message_ids', 'yash']
        fields_list = [field_name for field_name in request.env[model]._model_fields if field_name not in pop_list]
        return fields_list

    def fetch_remote_data(self, model_name, ids, remote_server_db, uid, remote_server_admin_user_password,
                          remote_db_access_models):
        """Fetches data for specific IDs from the remote server."""
        # current_running_db_server = request.env.company.current_running_db_server
        # remote_server_url = request.env.company.remote_server_url
        # # XML-RPC endpoints
        # common_url = f"{remote_server_url}/xmlrpc/2/common"
        # object_url = f"{remote_server_url}/xmlrpc/object"
        # remote_server_url = request.env.company.remote_server_url
        # remote_server_db = request.env.company.remote_server_db
        # remote_server_admin_user_name = request.env.company.remote_server_admin_user_name
        # remote_server_admin_user_password = request.env.company.remote_server_admin_user_password
        # common = xmlrpc.client.ServerProxy(common_url)
        # uid = common.authenticate(remote_server_db, remote_server_admin_user_name,
        #                           remote_server_admin_user_password,
        #                           {})
        # models = xmlrpc.client.ServerProxy(object_url)
        models = remote_db_access_models
        return models.execute_kw(
            remote_server_db, uid, remote_server_admin_user_password,
            model_name, 'read', [ids], {'fields': FIELDS[model_name]}
        )

    def process_many2one_field(self, comodel_name, field_value, remote_server_db, uid,
                               remote_server_admin_user_password, remote_db_access_models):
        """Handles many2one fields by mapping the remote ID to the local ID."""
        if not field_value:
            return False
        related_records_domain = [('remote_server_db_id', '=', field_value[0])]
        if 'active' in list(request.env[comodel_name]._fields):
            related_records_domain.append(('active','in',[True,False]))
        related_record = request.env[comodel_name].search(related_records_domain,limit=1)
        if related_record:
            return related_record.id
        else:
            # Fetch the related record data, including relational fields
            related_data = self.fetch_remote_data(comodel_name, [field_value[0]], remote_server_db, uid,
                                                  remote_server_admin_user_password, remote_db_access_models)
            for field, value in related_data[0].items():
                related_data[0][field] = self.handle_field_type(comodel_name, field, value, related_data[0],
                                                                remote_server_db, uid,
                                                                remote_server_admin_user_password,
                                                                remote_db_access_models)
            related_data[0].pop('id')
            return request.env[comodel_name].create(related_data[0]).id

    def process_one2many_field(self, model_name, comodel_name, field_value, remote_server_data, remote_server_db, uid,
                               remote_server_admin_user_password, remote_db_access_models):
        """Handles one2many fields by creating or updating related records."""
        related_ids = []
        for related_id in field_value:
            related_records_domain = [('remote_server_db_id', '=', related_id)]
            if 'active' in list(request.env[comodel_name]._fields):
                related_records_domain.append(('active', 'in', [True, False]))
            related_record = request.env[comodel_name].search(related_records_domain,limit=1)
            if related_record:
                related_ids.append((1, related_record.id, {}))  # Update existing record if necessary
            else:
                related_data = self.fetch_remote_data(comodel_name, [related_id], remote_server_db, uid,
                                                      remote_server_admin_user_password, remote_db_access_models)
                for field, value in related_data[0].items():
                    related_data[0][field] = self.handle_field_type(comodel_name, field, value,
                                                                    related_data[0], remote_server_db, uid,
                                                                    remote_server_admin_user_password,
                                                                    remote_db_access_models)
                related_data[0].pop('id')
                created_record = request.env[comodel_name].create(related_data[0])
                related_ids.append((4, created_record.id))  # Link to newly created record
        return related_ids

    def process_many2many_field(self, comodel_name, field_value, remote_server_db, uid,
                                remote_server_admin_user_password, remote_db_access_models):
        """Handles many2many fields by mapping remote IDs to local IDs."""
        related_ids = []
        for remote_id in field_value:
            related_records_domain = [('remote_server_db_id', '=', remote_id)]
            if 'active' in list(request.env[comodel_name]._fields):
                related_records_domain.append(('active', 'in', [True, False]))
            related_record = request.env[comodel_name].search(related_records_domain,limit=1)
            if related_record:
                related_ids.append(related_record.id)
            else:
                related_data = self.fetch_remote_data(comodel_name, [remote_id], remote_server_db, uid,
                                                      remote_server_admin_user_password, remote_db_access_models)
                for field, value in related_data[0].items():
                    related_data[0][field] = self.handle_field_type(comodel_name, field, value,
                                                                    related_data[0], remote_server_db, uid,
                                                                    remote_server_admin_user_password,
                                                                    remote_db_access_models)
                related_data[0].pop('id')
                new_record = request.env[comodel_name].create(related_data[0])
                related_ids.append(new_record.id)
        return [(6, 0, related_ids)]

    def handle_field_type(self, model_name, field_name, field_value, remote_server_data, remote_server_db, uid,
                          remote_server_admin_user_password, remote_db_access_models):
        """
        Handles different field types (many2one, one2many, many2many) for synchronization.

        :param env: Odoo environment
        :param model_name: Name of the model being processed
        :param field_name: Name of the field being processed
        :param field_value: The value of the field from the remote server
        :param remote_server_data: XML-RPC data dictionary from the remote server
        :return: Processed field value for local record creation or update
        """
        model = request.env[model_name]
        model_rec = request.env['ir.model'].search([('model', '=', model_name)], limit=1)
        field = model._fields[field_name]
        field_type = field.type
        fields_comodel_relation = request.env['ir.model.fields'].search([
            ('model_id', '=', model_rec.id),
            ('name', '=', field_name)
        ]).relation
        # fields_comodel_relation =
        if model_name != fields_comodel_relation:
            if field_type == 'many2one':
                return self.process_many2one_field(field.comodel_name, field_value, remote_server_db, uid,
                                                   remote_server_admin_user_password, remote_db_access_models)

            elif field_type == 'one2many':
                return self.process_one2many_field(model_name, field.comodel_name, field_value, remote_server_data,
                                                   remote_server_db, uid, remote_server_admin_user_password,
                                                   remote_db_access_models)

            elif field_type == 'many2many':
                return self.process_many2many_field(field.comodel_name, field_value, remote_server_db, uid,
                                                    remote_server_admin_user_password, remote_db_access_models)
            else:
                return field_value  # Return as-is for non-relational fields

    def batch_process_records(self, model, updates_domain, remote_server_db, uid, remote_server_admin_user_password,
                              remote_db_access_models):
        """Fetch records in batches and process them."""
        offset = 0
        while True:
            # if model =='product.template':
            #     # offset=500
            # Fetch a batch of records using limit and offset
            batch = remote_db_access_models.execute_kw(
                remote_server_db, uid, remote_server_admin_user_password,
                model, 'search_read', [updates_domain],
                {'fields': FIELDS[model], 'limit': BATCH_SIZE, 'offset': offset}
            )
            if not batch:
                break  # No more records, exit the loop

            # Process each record in the batch
            for record in batch:
                # Process the record (update or create it locally)
                self.process_record(model, record, remote_server_db, uid, remote_server_admin_user_password,
                                    remote_db_access_models)

            # Move to the next batch
            offset += BATCH_SIZE

    def process_record(self, model, server_rec, remote_server_db, uid, remote_server_admin_user_password,
                       remote_db_access_models):
        """Process a single record (update or create)."""
        server_rec_db_id = server_rec.get('id')
        server_rec.pop('id')  # Remove the remote ID for local processing
        server_rec.update({'remote_server_db_id': server_rec_db_id})
        print(f"{model} ================>{server_rec_db_id}")
        # Handle field types (many2one, one2many, many2many, etc.)
        try:
            for field_name, field_value in server_rec.items():
                server_rec[field_name] = self.handle_field_type(
                    model, field_name, field_value, server_rec, remote_server_db, uid,
                    remote_server_admin_user_password, remote_db_access_models
                )

            # Try to update the record in the local DB, if it exists
            rec_in_local_db = request.env[model].search([('remote_server_db_id', '=', server_rec_db_id)])
            if rec_in_local_db:
                rec_in_local_db.sudo().write(server_rec)  # Update the record
            else:
                request.env[model].sudo().create(server_rec)  # Create new record
        except Exception as e:
            print(e)
        _logger.info(f"Processed {model} record with remote_server_db_id {server_rec_db_id}")
    @http.route()
    def pos_web(self, config_id=False, **k):
        if request.env.company.current_running_db_server == 'local_server':
            last_remote_data_fetched_date_utc = request.env.company.remote_server_last_synced_data_time
            if not last_remote_data_fetched_date_utc:
                # For the first time call
                last_remote_data_fetched_date_utc = datetime.strptime("11-Nov-1990", "%d-%b-%Y")

            current_running_db_server = request.env.company.current_running_db_server
            remote_server_url = request.env.company.remote_server_url
            remote_server_db = request.env.company.remote_server_db
            remote_server_admin_user_name = request.env.company.remote_server_admin_user_name
            remote_server_admin_user_password = request.env.company.remote_server_admin_user_password

            # XML-RPC endpoints
            common_url = f"{remote_server_url}/xmlrpc/2/common"
            object_url = f"{remote_server_url}/xmlrpc/object"

            if current_running_db_server == 'local_server' and remote_server_url and self.is_internet_available() and self.is_server_accessible(
                    remote_server_url):
                common = xmlrpc.client.ServerProxy(common_url)
                uid = common.authenticate(remote_server_db, remote_server_admin_user_name,
                                          remote_server_admin_user_password, {})
                models = xmlrpc.client.ServerProxy(object_url)

                remote_db_access_models = models
                models_list = ['account.tax.group', 'account.tax', 'product.category', 'pos.category', 'stock.location',
                               'stock.warehouse', 'stock.picking.type',
                               'account.payment.method', 'account.journal', 'pos.payment.method',
                               'res.partner.industry', 'account.fiscal.position', 'account.fiscal.position.tax',
                               'account.payment.term', 'account.payment.term.line', 'crm.team', 'res.partner.category',
                               'res.bank', 'res.partner.bank', 'product.pricelist',
                               'uom.category', 'uom.uom', 'res.partner', 'product.template', 'product.pricelist.item',
                               'multi.barcode.products', 'product.multi.barcode',
                               'hr.department', 'hr.employee']

                for model in models_list:
                    updates_domain = [('write_date', '>', last_remote_data_fetched_date_utc)]
                    if request.env[model]._fields.get('active'):
                        updates_domain.append(('active', '=', True))
                    if request.env[model]._fields.get('company_id') and model not in ['product.template',
                                                                                      'product.pricelist',
                                                                                      'product.pricelist.item',
                                                                                      'res.partner']:
                        updates_domain.append(('company_id', '=', request.env.company.remote_server_db_id))

                    # Fetch and process records in batches
                    self.batch_process_records(model, updates_domain, remote_server_db, uid,
                                               remote_server_admin_user_password, remote_db_access_models)

                # Update last sync time
                request.env.company.remote_server_last_synced_data_time = datetime.now()

        res = super().pos_web(config_id=False, **k)
        return res

#     @http.route('/pos_in_offline_mode_with_sync_db/pos_in_offline_mode_with_sync_db/objects/', auth='public')
#     def list(self, **kw):
#         return http.request.render('pos_in_offline_mode_with_sync_db.listing', {
#             'root': '/pos_in_offline_mode_with_sync_db/pos_in_offline_mode_with_sync_db',
#             'objects': http.request.env['pos_in_offline_mode_with_sync_db.pos_in_offline_mode_with_sync_db'].search([]),
#         })

#     @http.route('/pos_in_offline_mode_with_sync_db/pos_in_offline_mode_with_sync_db/objects/<model("pos_in_offline_mode_with_sync_db.pos_in_offline_mode_with_sync_db"):obj>/', auth='public')
#     def object(self, obj, **kw):
#         return http.request.render('pos_in_offline_mode_with_sync_db.object', {
#             'object': obj
#         })
