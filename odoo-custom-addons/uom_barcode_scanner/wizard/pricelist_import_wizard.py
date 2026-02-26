from odoo import models, fields, api, _
from odoo.exceptions import UserError
import base64
import xlrd
from datetime import datetime
import re

class PricelistImportWizard(models.TransientModel):
    _name = "pricelist.import.wizard"
    _description = "Import Pricelist From Excel"

    file = fields.Binary("Upload File", required=True)
    filename = fields.Char("Filename")
    is_update = fields.Boolean("Update Price Rule")

    @api.model
    def _read_excel(self, file_content):
        workbook = xlrd.open_workbook(file_contents=file_content)
        sheet = workbook.sheet_by_index(0)
        rows = []

        for row_idx in range(1, sheet.nrows): 
            row_dict = {}
            for col_idx in range(sheet.ncols):
                value = sheet.cell_value(row_idx, col_idx)
                row_dict[col_idx] = value
            rows.append(row_dict)
        
        return rows

    def action_update_pricelist(self):
        if not self.file:
            raise UserError(_("Please upload an Excel file."))

        file_content = base64.b64decode(self.file)
        rows = self._read_excel(file_content)
        COLS = {
            "id": 0,
            "pricelist_name": 1,
            "discount_policy": 2,
            "selectable": 3,
            "apply_on": 4,
            "barcode": 5,
            "pricerule_id": 6,
            "min_qty": 7,
            "fixed_price": 8,
            "price_discount": 9,
            "product_template": 10,
        }

        for row in rows:

            pricelist_id = int(row[COLS["id"]])
            if not pricelist_id:
                raise UserError(_("Pricelist ID missing or invalid in row: %s") % row)

            pricelist = self.env["product.pricelist"].browse(pricelist_id)

            # sequence = row[COLS["sequence"]]

            discount_policy = row[COLS["discount_policy"]]
            discount_policy_val = "with_discount" if discount_policy.lower() == " discount included in the price" else "without_discount"

            TRUE_VALUES = {"true", "1", "t"}
            raw_value = str(row[COLS["selectable"]]).strip().lower()
            if raw_value.replace(".", "", 1).isdigit():
                raw_value = str(int(float(raw_value)))
            selectable = 1 if raw_value in TRUE_VALUES else 0

            pricelist_vals = {
                    'name': pricelist.name,
                    # 'sequence': sequence,
                    'discount_policy': discount_policy_val,
                    'selectable': selectable,
            }

            pricelist.write(pricelist_vals)

            # -----------------------------------------------------------
                # PRICERULE CREATION
            # -----------------------------------------------------------
            item_id = int(row[COLS["pricerule_id"]])
            if not item_id:
                raise UserError(_("Pricelist Item ID missing or invalid for row: %s") % row)

            pricelist_item = self.env["product.pricelist.item"].browse(item_id)

            if not pricelist_item.exists():
                raise UserError(_("Pricelist Item not found"))

            apply_on_value = str(row[COLS["apply_on"]]).strip().lower()
            APPLY_ON_MAP = [
                ("variant", "0_product_variant"),
                ("product category", "2_product_category"),
                ("category", "2_product_category"),
                ("all", "3_global"),
                ("product", "1_product"),
            ]
            applied_on = False
            for key, value in APPLY_ON_MAP:
                if key in apply_on_value:
                    applied_on = value
                    break

            barcode = str(row[COLS["barcode"]]).replace(".0", "").strip()
            min_qty = row[COLS["min_qty"]]
            fixed_price = row[COLS["fixed_price"]]
            price_discount = row[COLS["price_discount"]]
            product_name = row[COLS["product_template"]]

            if barcode:
                product_template = self.env['product.template'].search([('barcode', '=', barcode),('active', 'in', [True, False])], limit=1)
                if not product_template:
                    product_template = self.env['product.template'].search([('name', '=', product_name), ('active', 'in', [True, False])], limit=1)

            item_vals = {
                'applied_on': applied_on,
                'x_scanned_barcode': barcode if barcode else False,
                'min_quantity': min_qty if min_qty else False,
                'fixed_price': fixed_price if fixed_price else False,
                'price_discount': price_discount if price_discount else 0,
                'product_tmpl_id': product_template.id if product_template else False,
            }

            pricelist_item.write(item_vals)

        return {
            'effect': {
                'fadeout': 'slow',
                'message': _("Pricelist Update Completed Successfully!"),
                'type': 'rainbow_man',
            }
        }

    def action_import_pricelist(self):
        if self.is_update:
            self.action_update_pricelist()
        else:
            if not self.file:
                raise UserError(_("Please upload an excel file."))

            file_content = base64.b64decode(self.file)
            rows = self._read_excel(file_content)

            COLS = {
                "name": 0,
                "company": 1,
                "discount_policy": 2,
                "compute_price": 3,
                "active": 4,
                "apply_on": 5,
                "barcode": 6,
                "product": 7,
                "fixed_price": 8,
                "start_date": 9,    
                "end_date": 10,
                "min_qty": 11,
                "percentage_price": 12,
                "based_on": 13,
                "other_pricelist": 14,
                "price_discount": 15,
                "max_price_margin": 16,
                "min_price_margin": 17,
            }

            for row in rows:
                pricelist_name = row[COLS["name"]]
                # sequence = row[COLS["sequence"]]
                company_name = row[COLS["company"]]

                TRUE_VALUES = {"true", "1", "t"}
                normalize = lambda v: (
                    str(int(float(v))) if v.replace('.', '', 1).isdigit() else v
                ).strip().lower()

                active = 1 if normalize(str(row[COLS["active"]])) in TRUE_VALUES else 0
                # selectable = 1 if normalize(str(row[COLS["selectable"]])) in TRUE_VALUES else 0
                
                company_id = self.env['res.company'].search([('name', '=ilike', company_name)], limit=1).id
                
                discount_policy = row[COLS["discount_policy"]]
                if discount_policy.lower() == " discount included in the price":
                    discount_policy_val = "with_discount"
                else:
                    discount_policy_val = "without_discount"

                pricelist = self.env['product.pricelist'].search([('name', '=', pricelist_name)], limit=1)

                if not pricelist:
                    pricelist = self.env['product.pricelist'].create({
                        'name': pricelist_name,
                        # 'sequence': sequence,
                        'company_id': company_id,
                        'discount_policy': discount_policy_val,
                        'active': active,
                        # 'selectable': selectable,
                    })
                # -----------------------------------------------------------
                    # PRICERULE CREATION
                # -----------------------------------------------------------

                barcode = str(row[COLS["barcode"]]).strip()
                if barcode.replace('.', '', 1).isdigit():
                    try:
                        barcode = str(int(float(barcode)))
                    except:
                        pass
                # product_name = row[COLS["product"]]
                if barcode:
                    product = self.env['product.product'].search([('barcode', '=', barcode),('active', 'in', [True, False])], limit=1)
                    product_template = self.env['product.template'].search([('barcode', '=', barcode),('active', 'in', [True, False])], limit=1)
                
                compute_price_raw = str(row[COLS["compute_price"]]).strip().lower()
                VALID_COMPUTE_PRICE = {
                    "fixed": "fixed",
                    "percentage": "percentage",
                    "formula": "formula",
                }
                compute_price = False
                for key, value in VALID_COMPUTE_PRICE.items():
                    if key in compute_price_raw:   
                        compute_price = value
                        break

                apply_on_value = str(row[COLS["apply_on"]]).strip().lower()
                APPLY_ON_MAP = [
                    ("variant", "0_product_variant"),
                    ("product category", "2_product_category"),
                    ("category", "2_product_category"),
                    ("all", "3_global"),
                    ("product", "1_product"),
                ]
                applied_on = False
                for key, value in APPLY_ON_MAP:
                    if key in apply_on_value:
                        applied_on = value
                        break
                fixed_price = float(row[COLS["fixed_price"]]) if row[COLS["fixed_price"]] else 0
                min_qty = float(row[COLS["min_qty"]]) if row[COLS["min_qty"]] else 0

                def convert_excel_date(value):
                    if not value:
                        return False
                    try:
                        return datetime(*xlrd.xldate_as_tuple(value, 0)).date()
                    except:
                        return False
                start_date = convert_excel_date(row[COLS["start_date"]])
                end_date = convert_excel_date(row[COLS["end_date"]])

                percentage_price = row[COLS["percentage_price"]] 

                based_on = row[COLS["based_on"]].lower()
                if based_on in ["list price", "list_price", "sales price"]:
                    based_on = "list_price"
                elif based_on in ["cost", "standard_price", "standard price"]:
                    based_on = "standard_price"
                elif based_on in ["other pricelist", "pricelist", "other_pricelist"]:
                    based_on = "pricelist"

                other_pricelist = row[COLS["other_pricelist"]]
                other_pricelist = self.env['product.pricelist'].search([('name', '=', other_pricelist)], limit=1)

                price_discount = row[COLS["price_discount"]]
                max_price_margin = row[COLS["max_price_margin"]]
                min_price_margin = row[COLS["min_price_margin"]]

                item_vals = {
                    'pricelist_id': pricelist.id,
                    'x_scanned_barcode': barcode if barcode else False,
                    'compute_price': compute_price,
                    'applied_on': applied_on,
                    'fixed_price': fixed_price,
                    'min_quantity': min_qty,
                    'date_start': start_date,
                    'date_end': end_date,
                    'percent_price': percentage_price if percentage_price else 0,
                    'base': based_on,
                    'base_pricelist_id': other_pricelist.id if other_pricelist else False,
                    'price_discount': price_discount if price_discount else 0,
                    'price_max_margin': max_price_margin if max_price_margin else 0,
                    'price_min_margin': min_price_margin if min_price_margin else 0,
                    'product_id': product.id if product else False,
                    'product_tmpl_id': product_template.id if product_template else False,
                    'uom_id': product_template.uom_id.id if product_template else False,
                    'categ_id': product_template.categ_id.id if product_template else False,
                }

                rule = self.env['product.pricelist.item'].create(item_vals)

            return {
                'effect': {
                    'fadeout': 'slow',
                    'message': _("Pricelist Import Completed Successfully!"),
                    'type': 'rainbow_man',
                }
            }