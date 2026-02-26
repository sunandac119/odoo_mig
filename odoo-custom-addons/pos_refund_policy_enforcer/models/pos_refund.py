# -*- coding: utf-8 -*-
# Copyright 2025
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).
from odoo import api, fields, models, _
from odoo.exceptions import UserError, ValidationError
from odoo.tests import Form

class PosOrder(models.Model):
    _inherit = "pos.order"

    # Link between original and refund orders
    returned_order_id = fields.Many2one(
        comodel_name="pos.order",
        string="Returned Order",
        readonly=True,
    )
    refund_order_ids = fields.One2many(
        comodel_name="pos.order",
        inverse_name="returned_order_id",
        string="Refund Orders",
        readonly=True,
    )
    refund_order_qty = fields.Integer(
        compute="_compute_refund_order_qty",
        string="Refund Orders Quantity",
    )

    @api.depends('refund_order_ids')
    def _compute_refund_order_qty(self):
        order_data = self.env["pos.order"].read_group(
            [("returned_order_id", "in", self.ids)],
            ["returned_order_id"],
            ["returned_order_id"],
        )
        mapped_data = {
            order["returned_order_id"][0]: order["returned_order_id_count"]
            for order in order_data
        }
        for order in self:
            order.refund_order_qty = mapped_data.get(order.id, 0)

    def _blank_refund(self, res):
        self.ensure_one()
        new_order = self.browse(res["res_id"])
        new_order.returned_order_id = self
        new_order.lines.unlink()
        return new_order

    def _prepare_invoice_vals(self):
        res = super()._prepare_invoice_vals()
        if not self.returned_order_id.account_move:
            return res
        res.update({
            "invoice_origin": self.returned_order_id.account_move.name,
            "name": _("Return of %s" % self.returned_order_id.account_move.name),
            "reversed_entry_id": self.returned_order_id.account_move.id,
        })
        return res

    def _action_pos_order_invoice(self):
        self.action_pos_order_invoice()
        self.action_view_invoice()

    # ---- Policy Helper ----
    def _find_active_session_for_refund(self):
        """Find an opened session for the current user, else (if accounting user) any opened session on same config."""
        self.ensure_one()
        session = self.env['pos.session'].search([
            ('state', '=', 'opened'),
            ('config_id', '=', self.session_id.config_id.id),
            ('user_id', '=', self.env.uid)
        ], limit=1)

        if not session and self.env.user.has_group('account.group_account_user'):
            session = self.env['pos.session'].search([
                ('state', '=', 'opened'),
                ('config_id', '=', self.session_id.config_id.id)
            ], limit=1)

        if not session:
            raise UserError(_("To return product(s), you need to open a session in the POS %s") % self.session_id.config_id.display_name)

        return session

    def _check_refund_policy(self, session, is_partial=False):
        """Enforce refund rules: group, branch/company, new session, and prevent multiple full refunds."""
        self.ensure_one()

        # 1) Only Chief Cashier (or your chosen group)
        if not self.env.user.has_group('pos_refund_policy_enforcer.group_pos_chief_cashier'):
            raise UserError(_("Only Chief Cashier users can process returns."))

        # 2) Same branch as the original order's POS config (fallback to company)
        original_cfg = self.session_id.config_id
        refund_cfg = session.config_id
        has_branch = hasattr(original_cfg, 'branch_id') and hasattr(refund_cfg, 'branch_id')
        if has_branch and original_cfg.branch_id and refund_cfg.branch_id:
            if refund_cfg.branch_id.id != original_cfg.branch_id.id:
                raise UserError(_("You can only return orders in the same branch as the original sale."))
        else:
            if refund_cfg.company_id.id != original_cfg.company_id.id:
                raise UserError(_("You can only return orders in the same company as the original sale."))

        # 3) Must be a NEW session (not the same session that created the original order)
        if session.id == self.session_id.id:
            raise UserError(_("Returns must be processed in a NEW POS session (different from the original order's session)."))

        # 4) Prevent multiple full refunds of the same order
        if not is_partial and self.refund_order_qty and self.refund_order_qty > 0:
            raise UserError(_("This order has already been refunded. Use the Partial Refund wizard for remaining items."))

    # ---- Refund Entrypoints ----
    def refund(self):
        # Ensure POS session is open
        session = self._find_active_session_for_refund()

        # Enforce policy (full refund path)
        self._check_refund_policy(session, is_partial=False)

        # Allow negative qty creation (system-driven refund)
        ctx = dict(self.env.context, do_not_check_negative_qty=True, active_id=session.id)
        res = super(PosOrder, self.with_context(ctx)).refund()
        new_order = self._blank_refund(res)

        # Copy full negative quantities
        for line in self.lines:
            qty = -line.max_returnable_qty([])
            if qty != 0:
                copy_line = line.copy({
                    "order_id": new_order.id,
                    "returned_line_id": line.id,
                    "qty": qty,
                })
                copy_line._onchange_amount_line_all()
        new_order._onchange_amount_all()
        return res

    def partial_refund(self, partial_return_wizard):
        # Ensure POS session is open
        session = self._find_active_session_for_refund()

        # Enforce policy (partial refund path)
        self._check_refund_policy(session, is_partial=True)

        ctx = dict(self.env.context, partial_refund=True, active_id=session.id)
        res = self.with_context(ctx).refund()

        new_order = self._blank_refund(res)
        # Copy only selected lines/qty
        for wizard_line in partial_return_wizard.line_ids:
            qty = -wizard_line.qty
            if qty != 0:
                copy_line = wizard_line.pos_order_line_id.copy({
                    "order_id": new_order.id,
                    "returned_line_id": wizard_line.pos_order_line_id.id,
                    "qty": qty,
                })
                copy_line._onchange_amount_line_all()
        new_order._onchange_amount_all()
        return res

    def action_pos_order_paid(self):
        res = super().action_pos_order_paid()
        if self.returned_order_id and self.returned_order_id.account_move:
            self._action_pos_order_invoice()
        return res

    def _get_picking_destination(self):
        picking_type = self.config_id.picking_type_id
        if self.partner_id.property_stock_customer:
            destination = self.partner_id.property_stock_customer
        elif not picking_type or not picking_type.default_location_dest_id:
            destination = self.env["stock.warehouse"]._get_partner_locations()[0]
        else:
            destination = picking_type.default_location_dest_id
        return destination

    def _create_picking_return(self):
        self.ensure_one()
        return_form = Form(self.env["stock.return.picking"].with_context(
            active_id=self.returned_order_id.picking_ids.filtered(
                lambda picking: picking.location_dest_id.usage == "customer"
            ).id,
            active_model="stock.picking",
        ))
        wizard = return_form.save()
        wizard.product_return_moves.filtered(
            lambda x: x.product_id not in self.mapped("lines.product_id")
        ).unlink()
        to_return = {}
        order_lines = self.lines
        for order_line in order_lines:
            to_return.setdefault(order_line.product_id, 0)
            if order_line.qty > 0:
                continue
            order_lines -= order_line
            to_return[order_line.product_id] += order_line.qty
        for move in wizard.product_return_moves:
            if abs(to_return[move.product_id]) < move.quantity:
                move.quantity = abs(to_return[move.product_id])
            to_return[move.product_id] -= move.quantity
        picking = self.env["stock.picking"].browse(wizard.create_returns()["res_id"])
        normal_picking = self.env["stock.picking"]._create_picking_from_pos_order_lines(
            self._get_picking_destination().id,
            order_lines,
            self.config_id.picking_type_id,
            self.partner_id,
        )
        for move in picking.move_lines:
            move.quantity_done = move.product_uom_qty
        picking._action_done()
        (picking | normal_picking).write({
            "pos_session_id": self.session_id.id,
            "pos_order_id": self.id,
            "origin": self.name,
        })
        return picking | normal_picking

    def _create_order_picking(self):
        self.ensure_one()
        if not self.returned_order_id.picking_ids:
            return super()._create_order_picking()
        self.picking_ids = self._create_picking_return()


class PosOrderLine(models.Model):
    _inherit = "pos.order.line"

    returned_line_id = fields.Many2one(
        comodel_name="pos.order.line",
        string="Returned Order",
        readonly=True,
    )
    refund_line_ids = fields.One2many(
        comodel_name="pos.order.line",
        inverse_name="returned_line_id",
        string="Refund Lines",
        readonly=True,
    )

    @api.model
    def max_returnable_qty(self, ignored_line_ids):
        qty = self.qty
        for refund_line in self.refund_line_ids:
            if refund_line.id not in ignored_line_ids:
                qty += refund_line.qty
        return round(max(qty, 0.0), 6)

    @api.constrains("returned_line_id", "qty")
    def _check_return_qty(self):
        if self.env.context.get("do_not_check_negative_qty", False):
            return True
        for line in self:
            if line.returned_line_id and -line.qty > line.returned_line_id.qty:
                raise ValidationError(_(
                    "You can not return %d %s of %s because the original "
                    "Order line only mentions %d %s."
                ) % (
                    -line.qty,
                    line.product_id.uom_id.name,
                    line.product_id.name,
                    line.returned_line_id.qty,
                    line.product_id.uom_id.name,
                ))
            if line.returned_line_id and -line.qty > line.returned_line_id.max_returnable_qty([line.id]):
                raise ValidationError(_(
                    "You can not return %d %s of %s because some refunds"
                    " have already been done. Maximum quantity allowed: %d %s."
                ) % (
                    -line.qty,
                    line.product_id.uom_id.name,
                    line.product_id.name,
                    line.returned_line_id.max_returnable_qty([line.id]),
                    line.product_id.uom_id.name,
                ))
            if not line.returned_line_id and line.qty < 0 and not line.product_id.product_tmpl_id.pos_allow_negative_qty:
                raise ValidationError(_(
                    "For legal and traceability reasons, you can not set a"
                    " negative quantity (%d %s of %s), without using "
                    "return wizard."
                ) % (
                    line.qty,
                    line.product_id.uom_id.name,
                    line.product_id.name
                ))

            # Strict optional rule: disallow more than one refund order per original line
            if line.returned_line_id and line.returned_line_id.refund_line_ids:
                other_refunds = line.returned_line_id.refund_line_ids - line
                if other_refunds:
                    raise ValidationError(_(
                        "A refund for this line has already been processed. Multiple refunds for the same line are not allowed."
                    ))