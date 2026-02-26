from odoo import api, fields, models


class ProductProduct(models.Model):
    _inherit = 'product.product'

    sale_quantity = fields.Float('Quantity', compute="_compute_sale_quantity", inverse="_inverse_sale_quantity", search="_search_sale_quantity")

    @api.depends_context('sale_order_id')
    def _compute_sale_quantity(self):
        order = self._get_contextual_sorder()
        if order:
            SaleOrderLine = self.env['sale.order.line']
            # if self.user_has_groups('project.group_project_user'):
            #     order = order.sudo()
            #     SaleOrderLine = SaleOrderLine.sudo()

            products_qties = SaleOrderLine.read_group([('id', 'in', order.order_line.ids)], ['product_id', 'product_uom_qty'], ['product_id'])
            qty_dict = dict([(x['product_id'][0], x['product_uom_qty']) for x in products_qties if x['product_id']])
            for product in self:
                product.sale_quantity = qty_dict.get(product.id, 0)
        else:
            self.sale_quantity = False

    def _inverse_sale_quantity(self):
        order = self._get_contextual_sorder()
        if order:
            for product in self:
                sale_lines = self.env['sale.order.line'].search([('order_id', '=', order.id), ('product_id', '=', product.id)])
                all_editable_lines = sale_lines.filtered(lambda l: l.qty_delivered == 0 or l.qty_delivered_method == 'manual' or l.state != 'done')
                diff_qty = product.sale_quantity - sum(sale_lines.mapped('product_uom_qty'))

                if all_editable_lines:  # existing line: change ordered qty (and delivered, if delivered method)
                    if diff_qty > 0:
                        vals = {
                            'product_uom_qty': all_editable_lines[0].product_uom_qty + diff_qty,
                        }
                        if product.service_type == 'manual':
                            vals['qty_delivered'] = all_editable_lines[0].product_uom_qty + diff_qty
                        all_editable_lines[0].with_context(fsm_no_message_post=True).write(vals)
                        continue
                    # diff_qty is negative, we remove the quantities from existing editable lines:
                    for line in all_editable_lines:
                        new_line_qty = max(0, line.product_uom_qty + diff_qty)
                        diff_qty += line.product_uom_qty - new_line_qty
                        vals = {
                            'product_uom_qty': new_line_qty
                        }
                        if product.service_type == 'manual':
                            vals['qty_delivered'] = new_line_qty
                        line.write(vals)
                        if diff_qty == 0:
                            break

                elif diff_qty > 0:  # create new SOL
                    vals = {
                        'order_id': order.id,
                        'product_id': product.id,
                        'product_uom_qty': diff_qty,
                        'product_uom': product.uom_id.id
                    }
                    if product.service_type == 'manual':
                        vals['qty_delivered'] = diff_qty

                    if order.pricelist_id.discount_policy == 'without_discount':
                        sol = self.env['sale.order.line'].new(vals)
                        sol._onchange_discount()
                        vals.update({'discount': sol.discount or 0.0})
                    self.env['sale.order.line'].create(vals)

    @api.model
    def _search_sale_quantity(self, operator, value):
        if not (isinstance(value, int) or (isinstance(value, bool) and value is False)):
            raise ValueError('Invalid value: %s' % (value))
        if operator not in ('=', '!=', '<=', '<', '>', '>=') or (operator == '!=' and value is False):
            raise ValueError('Invalid operator: %s' % (operator))

        order = self._get_contextual_sorder()
        if not order:
            return []
        op = 'inselect'
        if value is False:
            value = 0
            operator = '>='
            op = 'not inselect'
        query = """
            SELECT product_id
            FROM sale_order_line sol
            WHERE order_id = %s AND product_uom_qty {} %s
        """.format(operator)
        return [('id', op, (query, (order.id, value)))]

    @api.model
    def _get_contextual_sorder(self):
        order_id = self.env.context.get('sale_order_id')
        if order_id:
            return self.env['sale.order'].browse(int(order_id))
        return self.env['sale.order']

    def set_sale_quantity(self, quantity):
        values = []
        saleorder = self.env['sale.order'].browse(self.env.context.get('active_ids'))
        for product in self:
            line = saleorder.order_line.filtered(lambda x: x.product_id == product)
            if not line:
                values.append((0, 0, {'product_id': product.id, 'product_uom_qty': quantity}))
                saleorder.order_line = values
            if line:
                if quantity <= 0.00:
                    line.unlink()
                else:
                    line.update({'product_uom_qty': quantity})
        self.sale_quantity = quantity
        return True

    def sale_add_quantity(self):
        return self.set_sale_quantity(self.sudo().sale_quantity + 1)

    def sale_remove_quantity(self):
        return self.set_sale_quantity(self.sudo().sale_quantity - 1)
