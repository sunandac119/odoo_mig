from odoo import models, fields, api
from datetime import timedelta
from odoo.tools.float_utils import float_round


class ProductTemplate(models.Model):
    _inherit = 'product.template'

    def action_consolidate_child_stock(self):
        Product = self.env['product.product']
        StockQuant = self.env['stock.quant']
        Inventory = self.env['stock.inventory']
        internal_locations = self.env['stock.location'].search([('usage', '=', 'internal')])

        for template in self:
            print(f"▶ Consolidating for parent template: {template.name}")
            parent_product = Product.search([('product_tmpl_id', '=', template.id)], limit=1)
            if not parent_product:
                print("⛔ No parent product variant found. Skipping.")
                continue

            child_templates = self.env['product.template'].search([
                ('parent_template_id', '=', template.id)
            ])

            child_products = Product.search([
                ('product_tmpl_id', 'in', child_templates.ids)
            ])

            for location in internal_locations:
                consolidated_lines = {}

                quants = StockQuant.search([
                    ('location_id', '=', location.id),
                    ('quantity', '>', 0),
                    ('product_id', 'in', child_products.ids),
                ])

                for quant in quants:
                    child_product = quant.product_id
                    unit_qty = child_product.product_tmpl_id.unit_qty or 1.0
                    delta_qty = quant.quantity * unit_qty

                    rounding = parent_product.uom_id.rounding or 0.01
                    delta_qty = float_round(delta_qty, precision_rounding=rounding)

                    if delta_qty <= 0:
                        continue

                    # Zero out child product
                    child_key = (child_product.id, location.id)
                    consolidated_lines[child_key] = 0.0

                    # Add to parent product
                    parent_key = (parent_product.id, location.id)
                    consolidated_lines[parent_key] = consolidated_lines.get(parent_key, 0.0) + delta_qty

                if consolidated_lines:
                    line_vals = []
                    for (product_id, location_id), qty in consolidated_lines.items():
                        product = Product.browse(product_id)
                        rounded_qty = float_round(qty, precision_rounding=product.uom_id.rounding or 0.01)

                        line_vals.append((0, 0, {
                            'product_id': product_id,
                            'location_id': location_id,
                            'product_qty': rounded_qty,
                        }))

                    inventory = Inventory.create({
                        'name': f'Consolidation - {template.name} - {location.display_name}',
                        'location_ids': [(6, 0, [location.id])],
                        'line_ids': line_vals,
                    })

                    inventory.action_start()
                    inventory.action_validate()
                    print(f"✅ Inventory validated for location: {location.display_name}")
                else:
                    print(f"❌ No stock to consolidate at location: {location.display_name}")


# class ProductStockConsolidation(models.Model):
#     _inherit = 'stock.quant'
#
#     @api.model
#     def _cron_transfer_child_qty_to_parent(self):
#         print('_cron_transfer_child_qty_to_parent')
#
#         Product = self.env['product.product']
#         child_templates = self.env['product.template'].search([('parent_template_id', '=', 250768)])
#
#         if not child_templates:
#             print('No child templates found for template 250768')
#             return
#
#         child_products = Product.search([('product_tmpl_id', 'in', child_templates.ids)])
#         if not child_products:
#             print('No child products found.')
#             return
#
#         quants = self.env['stock.quant'].search([
#             ('product_id', 'in', child_products.ids),
#             ('quantity', '>', 0),
#             ('location_id.usage', '=', 'internal'),
#         ])
#
#         if not quants:
#             print('No relevant quants found.')
#             return
#
#         consolidated_lines = {}
#
#         for quant in quants:
#             child_product = quant.product_id
#             child_template = child_product.product_tmpl_id
#             parent_template = child_template.parent_template_id
#
#             # Get the parent product variant (first one)
#             parent_product = Product.search([
#                 ('product_tmpl_id', '=', parent_template.id)
#             ], limit=1)
#
#             if not parent_product:
#                 continue
#
#             unit_qty = child_template.unit_qty or 1.0
#             delta_qty = quant.quantity * unit_qty
#
#             if delta_qty <= 0:
#                 continue
#
#             # Round to parent product UOM
#             rounding = parent_product.uom_id.rounding or 0.01
#             delta_qty = float_round(delta_qty, precision_rounding=rounding)
#
#             # Set child quantity to 0
#             child_key = (child_product.id, quant.location_id.id)
#             consolidated_lines[child_key] = 0.0
#
#             # Add to parent quantity
#             parent_key = (parent_product.id, quant.location_id.id)
#             consolidated_lines[parent_key] = consolidated_lines.get(parent_key, 0.0) + delta_qty
#
#         # Create and validate inventory
#         if consolidated_lines:
#             grouped_by_location = {}
#             for (product_id, location_id), qty in consolidated_lines.items():
#                 grouped_by_location.setdefault(location_id, []).append((product_id, qty))
#
#             for location_id, product_qty_list in grouped_by_location.items():
#                 line_vals = []
#                 for product_id, qty in product_qty_list:
#                     if qty == 0:
#                         continue  # skip setting zero if not needed
#
#                     product = Product.browse(product_id)
#                     rounding = product.uom_id.rounding or 0.01
#                     rounded_qty = float_round(qty, precision_rounding=rounding)
#
#                     line_vals.append((0, 0, {
#                         'product_id': product_id,
#                         'location_id': location_id,
#                         'product_qty': rounded_qty,
#                     }))
#
#                 if not line_vals:
#                     continue
#
#                 inventory = self.env['stock.inventory'].create({
#                     'name': f'Auto Consolidation - {self.env["stock.location"].browse(location_id).display_name}',
#                     'location_ids': [(6, 0, [location_id])],
#                     'line_ids': line_vals,
#                 })
#
#                 inventory.action_start()
#                 inventory.action_validate()

    # @api.model
    # def _cron_transfer_child_qty_to_parent(self):
    #     print('_cron_transfer_child_qty_to_parent')
    #
    #     target_template_id = 250768  # Your target product.template ID
    #     internal_locations = self.env['stock.location'].search([('usage', '=', 'internal')])
    #     Product = self.env['product.product']
    #
    #     for location in internal_locations:
    #         consolidated_lines = {}
    #
    #         quants = self.env['stock.quant'].search([
    #             ('location_id', '=', location.id),
    #             ('quantity', '>', 0),
    #             ('product_id.product_tmpl_id', '=', target_template_id),
    #             ('product_id.product_tmpl_id.parent_template_id', '!=', False),
    #             ('product_id.product_tmpl_id.parent_template_id', '!=', 'product_id.product_tmpl_id')
    #         ])
    #
    #         for quant in quants:
    #             child_product = quant.product_id
    #             child_template = child_product.product_tmpl_id
    #             parent_template = child_template.parent_template_id
    #
    #             # Get the parent product variant (first one)
    #             parent_product = Product.search([
    #                 ('product_tmpl_id', '=', parent_template.id)
    #             ], limit=1)
    #
    #             if not parent_product:
    #                 continue
    #
    #             unit_qty = child_template.unit_qty or 1.0
    #             delta_qty = quant.quantity * unit_qty
    #
    #             # Round delta_qty to parent UoM rounding
    #             rounding = parent_product.uom_id.rounding or 0.01
    #             delta_qty = float_round(delta_qty, precision_rounding=rounding)
    #
    #             # Skip zero quantity transfers
    #             if delta_qty <= 0:
    #                 continue
    #
    #             # Set child quantity to 0
    #             child_key = (child_product.id, location.id)
    #             consolidated_lines[child_key] = 0.0
    #
    #             # Add to parent quantity
    #             parent_key = (parent_product.id, location.id)
    #             consolidated_lines[parent_key] = consolidated_lines.get(parent_key, 0.0) + delta_qty
    #
    #         if consolidated_lines:
    #             line_vals = []
    #
    #             for (product_id, location_id), qty in consolidated_lines.items():
    #                 product = Product.browse(product_id)
    #                 rounding = product.uom_id.rounding or 0.01
    #                 rounded_qty = float_round(qty, precision_rounding=rounding)
    #
    #                 line_vals.append((0, 0, {
    #                     'product_id': product_id,
    #                     'location_id': location_id,
    #                     'product_qty': rounded_qty,
    #                 }))
    #
    #             inventory = self.env['stock.inventory'].create({
    #                 'name': f'Auto Consolidation - {location.display_name}',
    #                 'location_ids': [(6, 0, [location.id])],
    #                 'line_ids': line_vals,
    #             })
    #
    #             inventory.action_start()
    #             inventory.action_validate()



    # @api.model
    # def _cron_transfer_child_qty_to_parent(self):
    #     print('_cron_transfer_child_qty_to_parent')
    #     internal_locations = self.env['stock.location'].search([('usage', '=', 'internal')])
    #
    #     for location in internal_locations:
    #         # Dictionary to hold final quantity to be set per (product_id, location_id)
    #         consolidated_lines = {}
    #
    #         quants = self.env['stock.quant'].search([
    #             ('location_id', '=', location.id),
    #             ('quantity', '>', 0),
    #             ('product_id.product_tmpl_id.parent_template_id', '!=', False),
    #             ('product_id.product_tmpl_id.parent_template_id', '!=', 'product_id.product_tmpl_id')
    #         ])
    #
    #         for quant in quants:
    #             child_product = quant.product_id
    #             child_template = child_product.product_tmpl_id
    #             parent_template = child_template.parent_template_id
    #
    #             # Get the parent product variant (assuming one variant per template)
    #             parent_product = self.env['product.product'].search([
    #                 ('product_tmpl_id', '=', parent_template.id)
    #             ], limit=1)
    #
    #             if not parent_product:
    #                 continue  # Skip if no matching parent product found
    #
    #             unit_qty = child_template.unit_qty or 1.0
    #             delta_qty = quant.quantity * unit_qty
    #
    #             # Reduce child qty to zero
    #             child_key = (child_product.id, location.id)
    #             consolidated_lines[child_key] = 0.0
    #
    #             # Accumulate to parent
    #             parent_key = (parent_product.id, location.id)
    #             consolidated_lines[parent_key] = consolidated_lines.get(parent_key, 0.0) + delta_qty
    #
    #         if consolidated_lines:
    #             line_vals = []
    #             for (product_id, location_id), qty in consolidated_lines.items():
    #                 product = self.env['product.product'].browse(product_id)
    #                 rounding = product.uom_id.rounding
    #                 rounded_qty = float_round(qty, precision_rounding=rounding)
    #
    #                 line_vals.append((0, 0, {
    #                     'product_id': product_id,
    #                     'location_id': location_id,
    #                     'product_qty': rounded_qty,
    #                 }))
    #
    #             inventory = self.env['stock.inventory'].create({
    #                 'name': f'Auto Consolidation - {location.display_name}',
    #                 'location_ids': [(6, 0, [location.id])],
    #                 'line_ids': line_vals,
    #             })
    #             inventory.action_start()
    #             inventory.action_validate()

    # @api.model
    # def _cron_transfer_child_qty_to_parent(self):
    #     print('_cron_transfer_child_qty_to_parent')
    #
    #     internal_locations = self.env['stock.location'].search([('usage', '=', 'internal')])
    #     for location in internal_locations:
    #         final_lines = {}
    #
    #         quants = self.env['stock.quant'].search([
    #             ('location_id', '=', location.id),
    #             ('quantity', '>', 0),
    #             ('product_id.product_tmpl_id.parent_template_id', '!=', False)
    #         ])
    #
    #         for quant in quants:
    #             child_product = quant.product_id
    #             child_qty = quant.quantity
    #             parent_template = child_product.product_tmpl_id.parent_template_id
    #
    #             # SAFETY CHECK HERE
    #             if not parent_template.product_variant_ids:
    #                 continue  # Skip if parent has no variant
    #
    #             parent_product = parent_template.product_variant_ids[0]
    #             unit_qty = child_product.product_tmpl_id.unit_qty or 1.0
    #             delta_qty = child_qty * unit_qty
    #
    #             # Zero out child quantity
    #             child_key = (child_product.id, location.id)
    #             final_lines[child_key] = 0.0
    #
    #             # Add to parent quantity
    #             parent_key = (parent_product.id, location.id)
    #             final_lines[parent_key] = final_lines.get(parent_key, 0.0) + delta_qty
    #
    #         if final_lines:
    #             adjustment_lines = []
    #             for (product_id, location_id), qty in final_lines.items():
    #                 adjustment_lines.append((0, 0, {
    #                     'product_id': product_id,
    #                     'location_id': location_id,
    #                     'product_qty': qty,
    #                 }))
    #
    #             inventory = self.env['stock.inventory'].create({
    #                 'name': 'Auto Consolidation - %s' % location.display_name,
    #                 'location_ids': [(6, 0, [location.id])],
    #                 'line_ids': adjustment_lines,
    #             })
    #
    #             inventory.action_start()
    #             inventory.action_validate()



    # @api.model
    # def _cron_transfer_child_qty_to_parent(self):
    #     #working in local
    #     print('_cron_transfer_child_qty_to_parent')
    #
    #     internal_locations = self.env['stock.location'].search([('usage', '=', 'internal')])
    #     for location in internal_locations:
    #         # Final dictionary to store (product_id, location_id): qty
    #         final_lines = {}
    #
    #         # Get all quants with child products that have a parent template
    #         quants = self.env['stock.quant'].search([
    #             ('location_id', '=', location.id),
    #             ('quantity', '>', 0),
    #             ('product_id.product_tmpl_id.parent_template_id', '!=', False)
    #         ])
    #
    #         for quant in quants:
    #             child_product = quant.product_id
    #             child_qty = quant.quantity
    #             parent_template = child_product.product_tmpl_id.parent_template_id
    #             parent_product = parent_template.product_variant_ids[0]
    #             unit_qty = child_product.product_tmpl_id.unit_qty or 1.0
    #             delta_qty = child_qty * unit_qty
    #
    #             # Child: Set qty to 0
    #             child_key = (child_product.id, location.id)
    #             final_lines[child_key] = 0.0  # Always overwrite to 0
    #
    #             # Parent: Add quantity (grouped)
    #             parent_key = (parent_product.id, location.id)
    #             if parent_key in final_lines:
    #                 final_lines[parent_key] += delta_qty
    #             else:
    #                 final_lines[parent_key] = delta_qty
    #
    #         if final_lines:
    #             adjustment_lines = []
    #             for (product_id, location_id), qty in final_lines.items():
    #                 adjustment_lines.append((0, 0, {
    #                     'product_id': product_id,
    #                     'location_id': location_id,
    #                     'product_qty': qty,
    #                 }))
    #
    #             inventory = self.env['stock.inventory'].create({
    #                 'name': 'Auto Consolidation - %s' % location.display_name,
    #                 'location_ids': [(6, 0, [location.id])],
    #                 'line_ids': adjustment_lines,
    #             })
    #
    #             inventory.action_start()
    #             inventory.action_validate()






# from odoo import models, api, _
#
# class ProductMerge(models.Model):
#     _inherit = 'stock.quant'
#
#     @api.model
#     def _cron_transfer_child_qty_to_parent(self):
#         print('_cron_transfer_child_qty_to_parent')
#         Location = self.env['stock.location']
#         Quant = self.env['stock.quant']
#         Inventory = self.env['stock.inventory']
#         ProductProduct = self.env['product.product']
#
#         internal_locations = Location.search([('usage', '=', 'internal')])
#
#         for location in internal_locations:
#             line_vals = []
#             products_done = set()
#             quants = Quant.search([
#                 ('location_id', '=', location.id),
#                 ('quantity', '>', 0),
#                 ('product_id.product_tmpl_id.parent_template_id', '!=', False),
#             ])
#
#             # Mapping: (child_product, location) -> quantity
#             for quant in quants:
#                 child_product = quant.product_id
#                 child_tmpl = child_product.product_tmpl_id
#                 parent_tmpl = child_tmpl.parent_template_id
#                 unit_qty = child_tmpl.unit_qty or 1.0
#                 parent_product = parent_tmpl.product_variant_id
#
#                 delta_qty = quant.quantity * unit_qty
#
#                 # Child: set counted quantity to 0
#                 line_vals.append((0, 0, {
#                     'product_id': child_product.id,
#                     'location_id': location.id,
#                     'product_qty': 0,
#                 }))
#
#                 # Parent: add delta
#                 if parent_product.id not in products_done:
#                     parent_qty = sum(Quant.search([
#                         ('product_id', '=', parent_product.id),
#                         ('location_id', '=', location.id)
#                     ]).mapped('quantity'))
#                     # parent_qty = Quant._get_inventory_quantity(parent_product, location)
#                     line_vals.append((0, 0, {
#                         'product_id': parent_product.id,
#                         'location_id': location.id,
#                         'product_qty': parent_qty + delta_qty,
#                     }))
#                     products_done.add(parent_product.id)
#
#             if line_vals:
#                 inventory = Inventory.create({
#                     'name': 'Auto Stock Merge - {}'.format(location.name),
#                     'filter': 'partial',
#                     'location_ids': [(6, 0, [location.id])],
#                     'line_ids': line_vals,
#                 })
#                 inventory.action_start()
#                 inventory.action_validate()

# class ProductTemplate(models.Model):
#     _inherit = 'product.template'
#
#     @api.model
#     def _cron_transfer_child_qty_to_parent(self):
#         Quant = self.env['stock.quant'].sudo()
#         Warehouse = self.env['stock.warehouse'].sudo()
#
#         parent_map = {}
#         templates = self.sudo().search([('parent_template_id', '!=', False)])
#
#         for child_template in templates:
#             parent = child_template.parent_template_id
#             if not parent or parent.id == child_template.id:
#                 continue  # skip self-parent or missing
#
#             child_product = child_template.product_variant_id
#             parent_product = parent.product_variant_id
#             if not child_product or not parent_product:
#                 continue
#
#             company = child_template.company_id or self.env.company
#             warehouse = Warehouse.search([('company_id', '=', company.id)], limit=1)
#             location = warehouse.lot_stock_id if warehouse else self.env.ref('stock.stock_location_stock')
#
#             qty_available = Quant._get_available_quantity(child_product, location, allow_negative=False)
#             if qty_available <= 0:
#                 continue
#
#             ctn_qty = child_template.ctn_qty or 1.0
#             transfer_qty = qty_available * ctn_qty
#
#             # 1. Deduct from child product quant
#             Quant._update_available_quantity(child_product, location, -qty_available)
#
#             # 2. Add to parent product quant
#             Quant._update_available_quantity(parent_product, location, transfer_qty)
#
#             # 3. Optional custom field update and messages
#             child_template.write({'parent_qty_available': 0.0})
#             parent.write({'parent_qty_available': (parent.parent_qty_available or 0.0) + transfer_qty})
#
#             msg = _(
#                 "Transferred %.2f (%.2f × %.2f) from Child Product <b>%s</b> "
#                 "to Parent Product <b>%s</b>. Child's qty set to 0."
#             ) % (
#                       transfer_qty, qty_available, ctn_qty,
#                       child_template.display_name,
#                       parent.display_name,
#                   )
#             child_product.message_post(body=msg)
#             parent_product.message_post(body=msg)

    # @api.model
    # def _cron_transfer_child_qty_to_parent(self):
    #     # Step 1: Initialize mapping for parent templates and child data
    #     parent_map = {}  # parent_template_id -> list of child records
    #     templates = self.sudo().search([('parent_template_id', '!=', False)])
    #
    #     for template in templates:
    #         parent = template.parent_template_id
    #         if not parent or template.id == parent.id:
    #             continue  # Skip if it's not a child
    #
    #         # Group by parent
    #         if parent.id not in parent_map:
    #             parent_map[parent.id] = []
    #         parent_map[parent.id].append(template)
    #
    #     # Step 2: For each parent, compute sum(child.qty_available * child.ctn_qty)
    #     for parent_id, children in parent_map.items():
    #         total_transfer_qty = 0.0
    #         for child in children:
    #             qty = child.qty_available or 0.0
    #             ctn_qty = child.ctn_qty or 1.0
    #             transfer_qty = qty * ctn_qty
    #             total_transfer_qty += transfer_qty
    #
    #             # Reset child's parent_qty_available
    #             child.write({'parent_qty_available': 0.0})
    #
    #             # Optional: log message on child
    #             msg = _(
    #                 "Transferred %.2f (%.2f × %.2f) to parent <b>%s</b>. Child's parent_qty_available set to 0."
    #             ) % (transfer_qty, qty, ctn_qty, child.parent_template_id.display_name)
    #             child.message_post(body=msg)
    #
    #         # Step 3: Write total to parent
    #         parent = self.browse(parent_id)
    #         parent.write({'parent_qty_available': total_transfer_qty})
    #
    #         # Optional: log message on parent
    #         parent.message_post(body=_(
    #             "Updated parent_qty_available to %.2f by summing all children."
    #         ) % total_transfer_qty)

    # @api.model
    # def _cron_transfer_child_qty_to_parent(self):
    #     Quant = self.env['stock.quant'].sudo()
    #     Warehouse = self.env['stock.warehouse'].sudo()
    #
    #     # Get all child templates (where parent_template_id is set and different from self)
    #     child_templates = self.sudo().search([
    #         ('parent_template_id', '!=', False),
    #         ('id', '!=', models.F('parent_template_id'))
    #     ])
    #
    #     for child_template in child_templates:
    #         parent_template = child_template.parent_template_id
    #
    #         child_product = child_template.product_variant_id
    #         parent_product = parent_template.product_variant_id
    #
    #         if not child_product or not parent_product:
    #             continue
    #
    #         company = child_template.company_id or self.env.company
    #         warehouse = Warehouse.search([('company_id', '=', company.id)], limit=1)
    #         stock_location = warehouse.lot_stock_id if warehouse else self.env.ref('stock.stock_location_stock')
    #
    #         # Get qty_available from stock for the child product in the location
    #         child_qty_available = Quant._get_available_quantity(child_product, stock_location, allow_negative=True)
    #         if child_qty_available <= 0:
    #             continue
    #
    #         # ctn_qty or unit_qty - assumed field on child template
    #         ctn_qty = child_template.ctn_qty or 1.0
    #         transfer_qty = child_qty_available * ctn_qty
    #
    #         # Transfer stock from child to parent
    #         Quant._update_available_quantity(child_product, stock_location, -child_qty_available)
    #         Quant._update_available_quantity(parent_product, stock_location, transfer_qty)
    #
    #         # Log messages on both products
    #         msg = _(
    #             "Transferred <b>%.2f</b> (%.2f × %.2f) from Child Product <b>%s</b> "
    #             "to Parent Product <b>%s</b>."
    #         ) % (
    #                   transfer_qty,
    #                   child_qty_available,
    #                   ctn_qty,
    #                   child_template.display_name,
    #                   parent_template.display_name,
    #               )
    #         parent_product.message_post(body=msg)
    #         child_product.message_post(body=msg)

    # @api.model
    # def _cron_transfer_child_qty_to_parent(self):
    #     Quant = self.env['stock.quant'].sudo()
    #     Warehouse = self.env['stock.warehouse'].sudo()
    #
    #     children = self.sudo().search([('parent_template_id', '!=', False)])
    #     for child_template in children:
    #         child_product = child_template.product_variant_id
    #         parent_template = child_template.parent_template_id
    #         parent_product = parent_template.product_variant_id
    #
    #         if not child_product or not parent_product:
    #             continue
    #
    #         company = child_template.company_id or self.env.company
    #         warehouse = Warehouse.search([('company_id', '=', company.id)], limit=1)
    #         stock_location = warehouse.lot_stock_id if warehouse else self.env.ref('stock.stock_location_stock')
    #
    #         child_qty_available = child_product.with_company(company.id).qty_available
    #         if child_qty_available <= 0:
    #             continue
    #
    #         unit_qty = child_template.unit_qty or 1.0
    #         transfer_qty = child_qty_available * unit_qty
    #
    #         Quant._update_available_quantity(child_product, stock_location, -child_qty_available)
    #         Quant._update_available_quantity(parent_product, stock_location, transfer_qty)
    #
    #         msg = _(
    #             "Child Product <b>%s</b> had qty <b>%.2f</b> × unit qty <b>%.2f</b> = <b>%.2f</b> "
    #             "moved to Parent Product <b>%s</b>. Now child is 0.",
    #         ) % (
    #             child_template.display_name,
    #             child_qty_available,
    #             unit_qty,
    #             transfer_qty,
    #             parent_template.display_name,
    #         )
    #         parent_product.message_post(body=msg)
    #         child_product.message_post(body=msg)
