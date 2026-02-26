from odoo import api, fields, models, _
from datetime import datetime


class StockRequest(models.Model):
    _name = "stock.request"
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _description = "Material Request"

    name = fields.Char(string="Number", readonly=True, required=True, copy=False, default='New')
    partner_id = fields.Many2one('res.partner', string='Contact')
    requested_by = fields.Many2one('res.users', string='Requested By', default=lambda self: self.env.user)
    approved_by = fields.Many2one('res.users', string='Approved By')
    branch_id = fields.Many2one('res.branch', string='Branch', help='The default branch for this user.',
                                context={'user_preference': True},  default=lambda self:  self.env.user.branch_id.id)
    stock_location_id = fields.Many2one(
        'stock.location',
        string='Source Location',
        default=lambda self: self.env['stock.picking.type']
        .browse(self._context.get('default_picking_type_id')).default_location_src_id,
        required=True
    )
    delivery_location_id = fields.Many2one(
        'stock.location',
        string='Destination Location',
        default=lambda self: self.env['stock.picking.type']
        .browse(self._context.get('default_picking_type_id')).default_location_dest_id,
        required=True
    )
    picking_type_id = fields.Many2one('stock.picking.type', string='Operation Type', required=True)
    requested_date = fields.Datetime(string="Requested Date", default=fields.Datetime.now)
    states = fields.Selection([
        ('draft', 'Draft'),
        ('confirmed', 'Confirmed'),
        ('approve', 'Approved'),
        ('receive', 'Received')],
        string='Status', readonly=True, copy=False, index=True, tracking=True, default='draft'
    )
    company_id = fields.Many2one('res.company', 'Company', required=True,
                                 default=lambda s: s.env.company.id, index=True)
    notes = fields.Text(string='Notes')
    stock_line_ids = fields.One2many('stock.request.lines', 'stock_request_id', string='Stock Request Lines')
    on_hand_quantity = fields.Integer("On Hand")
    picking_count = fields.Integer("#Picking", compute='compute_picking_count')

    @api.onchange('picking_type_id', 'partner_id')
    def onchange_picking_type(self):
        if self.picking_type_id and self.states == 'draft':
            self = self.with_company(self.company_id)
            if self.picking_type_id.default_location_src_id:
                location_id = self.picking_type_id.default_location_src_id.id
            elif self.partner_id:
                location_id = self.partner_id.property_stock_supplier.id
            else:
                customerloc, location_id = self.env['stock.warehouse']._get_partner_locations()

            if self.picking_type_id.default_location_dest_id:
                location_dest_id = self.picking_type_id.default_location_dest_id.id
            elif self.partner_id:
                location_dest_id = self.partner_id.property_stock_customer.id
            else:
                location_dest_id, supplierloc = self.env['stock.warehouse']._get_partner_locations()

            self.stock_location_id = location_id
            self.delivery_location_id = location_dest_id
            (self.stock_line_ids).update({
                "picking_type_id": self.picking_type_id,
                "company_id": self.company_id,
            })

    def action_on_hand_view(self):
        return {
            'name': 'On Hand',
            'view_type': 'form',
            'view_mode': 'tree,form',
            'res_model': 'stock.quant',
            'view_id': False,
            'type': 'ir.actions.act_window',
            'domain': [('product_id', 'in', self.stock_line_ids.mapped('product_id').ids)]
        }

    @api.depends('name')
    def compute_picking_count(self):
        stock_picking = self.env['stock.picking']
        for record in self:
            record.picking_count = stock_picking.search_count([('origin', '=', record.name)])

    def action_picking_view(self):
        return {
            'name': 'Picking',
            'view_type': 'form',
            'view_mode': 'tree,form',
            'res_model': 'stock.picking',
            'view_id': False,
            'type': 'ir.actions.act_window',
            'domain': [('origin', 'in', self.mapped('name'))],
        }

    @api.model
    def create(self, vals):
        if vals.get('name', _('New')) == _('New'):
            vals['name'] = self.env['ir.sequence'].next_by_code('stock.request') or _('New')
        result = super(StockRequest, self).create(vals)
        return result

    def action_confirm(self):
        for rec in self:
            rec.states = 'confirmed'

    def action_done(self):
        if self.env.user.has_group('stock.group_stock_manager'):
            for rec in self:
                rec.states = 'receive'

    def action_create_picking(self):
        if self.env.user.has_group('stock.group_stock_manager'):
            for record in self:
                picking_line = []
                picking_data = {
                    'partner_id': record.partner_id.id,
                    'picking_type_id': record.picking_type_id.id,
                    'origin': record.name,
                    'location_id': record.delivery_location_id.id,
                    'location_dest_id': record.stock_location_id.id,
                    'move_ids_without_package': picking_line,
                }
                for lines in record.stock_line_ids:
                    picking_line.append((0, 0, {
                        'product_id': lines.product_id.id,
                        'name': lines.description,
                        'product_uom_qty': lines.product_qty,
                        'location_id': record.delivery_location_id.id,
                        'location_dest_id': record.stock_location_id.id,
                        'product_uom': lines.product_id.uom_id.id
                    }))
                self.env['stock.picking'].create(picking_data)
                record.write({
                    'states': 'approve',
                    'approved_by': self.env.user,
                })

    def action_send_mail(self):
        self.ensure_one()
        template_id = self.env['ir.model.data'].xmlid_to_res_id('warehouse_stock_request_app.stock_request_email_template', raise_if_not_found=False)
        template = self.env['mail.template'].browse(template_id)
        attachment_obj = self.env['ir.attachment']
        attachments = attachment_obj.search([('res_id', '=', self.id), ('res_model', '=', 'stock.request')], limit=1)

        ctx = {
            'default_model': 'stock.request',
            'default_res_id': self.id,
            'default_use_template': bool(template_id),
            'default_template_id': template_id,
            'default_composition_mode': 'comment',
            'force_email': True,
            'default_attachment_ids': [(6, 0, attachments.ids)],
        }

        return {
            'type': 'ir.actions.act_window',
            'view_mode': 'form',
            'res_model': 'mail.compose.message',
            'views': [(False, 'form')],
            'view_id': False,
            'target': 'new',
            'context': ctx,
        }


class StockRequestLines(models.Model):
    _name = 'stock.request.lines'
    _description = "Stock Request lines"

    stock_request_id = fields.Many2one('stock.request', string='Stock Request')
    product_id = fields.Many2one('product.product', string='Product', required=True)
    description = fields.Text(string='Description', required=True)
    product_qty = fields.Float(string='Delivered Quantity', digits='Unit of Measure', default=1.0)
    product_uom = fields.Many2one('uom.uom', 'Unit of Measure', required=True)

    @api.onchange('product_id')
    def _onchange_product_id(self):
        if self.product_id:
            self.description = self.product_id.name
            self.product_uom = self.product_id.uom_id.id
