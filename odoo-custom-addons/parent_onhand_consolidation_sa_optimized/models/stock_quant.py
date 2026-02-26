from odoo import models, api
from datetime import datetime

class StockQuant(models.Model):
    _inherit = 'stock.quant'

    @api.model
    def consolidate_child_to_parent_by_location(self):
        Quant = self.env["stock.quant"]
        Product = self.env["product.product"]
        PT = self.env["product.template"]
        Location = self.env["stock.location"]

        internal_locs = Location.search([("usage", "=", "internal")])
        if not internal_locs:
            return

        child_tmpls = PT.search([("parent_template_id", "!=", False), ("unit_qty", ">", 0.0)])
        if not child_tmpls:
            return

        parent_variant_cache = {}
        child_to_parent = {}
        for ct in child_tmpls:
            pt = ct.parent_template_id
            if not pt:
                continue
            if pt.id not in parent_variant_cache:
                pv = pt.product_variant_id or pt.product_variant_ids[:1]
                if not pv:
                    continue
                parent_variant_cache[pt.id] = pv
            parent_prod = parent_variant_cache[pt.id]
            for cp in ct.product_variant_ids:
                child_to_parent[cp.id] = (parent_prod, ct.unit_qty)

        if not child_to_parent:
            return

        groups = Quant.read_group(
            domain=[
                ("product_id", "in", list(child_to_parent.keys())),
                ("location_id", "in", internal_locs.ids),
                ("quantity", "!=", 0.0),
            ],
            fields=["product_id", "location_id", "quantity"],
            groupby=["product_id", "location_id"],
            lazy=False,
        )

        parent_products = list({child_to_parent[pid][0].id for pid in child_to_parent})
        parent_groups = Quant.read_group(
            domain=[
                ("product_id", "in", parent_products),
                ("location_id", "in", internal_locs.ids),
            ],
            fields=["product_id", "location_id", "quantity"],
            groupby=["product_id", "location_id"],
            lazy=False,
        )
        parent_qty_map = {
            (g["product_id"][0], g["location_id"][0]): g["quantity"] for g in parent_groups
        }

        by_loc = {}
        for g in groups:
            loc_id = g["location_id"][0]
            child_pid = g["product_id"][0]
            qty = g["quantity"]
            by_loc.setdefault(loc_id, []).append((child_pid, qty))

        for loc_id, items in by_loc.items():
            loc = Location.browse(loc_id)
            parent_deltas = {}
            inv_line_map = {}

            for child_pid, qty_child in items:
                parent_prod, unit_qty = child_to_parent.get(child_pid, (False, 0.0))
                if not parent_prod or not unit_qty:
                    continue
                delta = qty_child * unit_qty
                parent_deltas[parent_prod.id] = parent_deltas.get(parent_prod.id, 0.0) + delta

                child_prod = Product.browse(child_pid)
                line_key = (child_prod.id, loc.id)
                if line_key not in inv_line_map:
                    inv_line_map[line_key] = {
                        "product_id": child_prod.id,
                        "product_uom_id": child_prod.uom_id.id,
                        "location_id": loc.id,
                        "product_qty": 0.0,
                    }

            for parent_pid, delta in parent_deltas.items():
                theo = parent_qty_map.get((parent_pid, loc.id), 0.0)
                parent_prod = Product.browse(parent_pid)
                line_key = (parent_prod.id, loc.id)
                if line_key in inv_line_map:
                    inv_line_map[line_key]["product_qty"] += delta
                else:
                    inv_line_map[line_key] = {
                        "product_id": parent_prod.id,
                        "product_uom_id": parent_prod.uom_id.id,
                        "location_id": loc.id,
                        "product_qty": theo + delta,
                    }

            inv_lines = [(0, 0, vals) for vals in inv_line_map.values()]
            if inv_lines:
                self.env["stock.inventory"].create({
                    "name": "Daily Consolidation - %s" % datetime.now().strftime("%Y-%m-%d"),
                    "company_id": loc.company_id.id,
                    "location_ids": [(6, 0, [loc.id])],
                    "prefill_counted_quantity": "zero",
                    "line_ids": inv_lines,
                })