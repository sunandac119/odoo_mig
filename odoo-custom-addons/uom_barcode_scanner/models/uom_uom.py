from odoo import models, fields, api, tools
from odoo.exceptions import ValidationError
from datetime import datetime, date
import logging

_logger = logging.getLogger(__name__)

class UomUom(models.Model):
    _inherit = 'uom.uom'

    @api.model
    def name_search(self, name='', args=None, operator='ilike', limit=100):
        if self.env.context.get("restrict_uom_product_tmpl_id"):
            tmpl_id = self.env.context["restrict_uom_product_tmpl_id"]
            tmpl = self.env["product.template"].browse(tmpl_id)
            allowed_uom_ids = tmpl.barcode_uom_ids.mapped("uom_id").ids
            args = args or []
            args.append(("id", "in", allowed_uom_ids))
        elif self.env.context.get("restrict_uom_product_tmpl_id_wizard"):
            tmpl_id = self.env.context["restrict_uom_product_tmpl_id_wizard"]
            tmpl = self.env["product.template"].browse(tmpl_id)
            allowed_uom_ids = tmpl.barcode_uom_ids.mapped("uom_id").ids
            args = args or []
            args.append(("id", "in", allowed_uom_ids))
        return super(UomUom, self).name_search(name, args, operator, limit)


    def _compute_quantity(self, qty, to_unit, round=True, rounding_method='UP', raise_if_failure=True):
        """ Convert the given quantity from the current UoM `self` into a given one
            :param qty: the quantity to convert
            :param to_unit: the destination UoM record (uom.uom)
            :param raise_if_failure: only if the conversion is not possible
                - if true, raise an exception if the conversion is not possible (different UoM category),
                - otherwise, return the initial quantity
        """
        if not self or not qty:
            return qty
        self.ensure_one()

        # if self != to_unit and self.category_id.id != to_unit.category_id.id:
        #     if raise_if_failure:
        #         raise UserError(_('The unit of measure %s defined on the order line doesn\'t belong to the same category as the unit of measure %s defined on the product. Please correct the unit of measure defined on the order line or on the product, they should belong to the same category.') % (self.name, to_unit.name))
        #     else:
        #         return qty

        if self == to_unit:
            amount = qty
        else:
            amount = qty / self.factor
            if to_unit:
                amount = amount * to_unit.factor

        if to_unit and round:
            amount = tools.float_round(amount, precision_rounding=to_unit.rounding, rounding_method=rounding_method)

        return amount