from odoo import models, api
from odoo.exceptions import UserError
import base64
import io
import xlsxwriter
from datetime import datetime


class Partner(models.Model):
    _inherit = "res.partner"

    def action_export_vendor_products_xlsx(self):
        if not self:
            raise UserError("Please select at least one vendor.")

        supplier_lines = self.env['product.supplierinfo'].search([
            ('name', 'in', self.ids)
        ])

        if not supplier_lines:
            raise UserError("No vendor products found for selected vendors.")

        output = io.BytesIO()
        workbook = xlsxwriter.Workbook(output)
        sheet = workbook.add_worksheet("Vendor Products")

        headers = ["Name", "Product Type", "Product Category", "Barcode", "UoM Category", "Unit Of Measure", "Unit Qty", "CTN Qty",
                   "Barcode UoMs/UOM Category", "Barcode UoMs/Description", "Barcode UoMs/Unit of Measure", "Barcode UoMs/Barcode", "Barcode UoMs/Sale Price",
                   "Vendors/Vendor", "Vendors/Quantity", "Vendors/Unit of Measure", "Vendors/Price", "Vendors/Discount (%)", "Vendors/Delivery Lead Time"]
        for col, header in enumerate(headers):
            sheet.write(0, col, header)

        row = 1

        for sup in supplier_lines:
            product = sup.product_tmpl_id

            barcode_uoms = product.barcode_uom_ids 
            vendor_records = product.seller_ids    

            max_rows = max(len(barcode_uoms), len(vendor_records), 1)

            for i in range(max_rows):
                barcode = barcode_uoms[i] if i < len(barcode_uoms) else False
                vendor = vendor_records[i] if i < len(vendor_records) else False

                sheet.write(row, 0, product.name or "")
                sheet.write(row, 1, product.type or "")
                sheet.write(row, 2, product.categ_id.name or "")
                sheet.write(row, 3, product.barcode or "")
                sheet.write(row, 4, product.uom_id.category_id.name or "")
                sheet.write(row, 5, product.uom_id.name or "")
                sheet.write(row, 6, product.qty_available or 0)
                sheet.write(row, 7, product.uom_id.name)

                # Barcode UoM data
                sheet.write(row, 8, barcode.uom_id.category_id.name if barcode else "")
                sheet.write(row, 9, barcode.description if barcode else "")
                sheet.write(row, 10, barcode.uom_id.name if barcode else "")
                sheet.write(row, 11, barcode.barcode if barcode else "")
                sheet.write(row, 12, barcode.sale_price if barcode else "")

                # Vendor data
                sheet.write(row, 13, vendor.name.name if vendor else "")
                sheet.write(row, 14, vendor.min_qty if vendor else "")
                sheet.write(row, 15, vendor.product_uom.name if vendor else "")
                sheet.write(row, 16, vendor.price if vendor else "")
                sheet.write(row, 17, vendor.delay if vendor else "")
                sheet.write(row, 18, vendor.discount if hasattr(vendor, "discount") else "")

                row += 1

        workbook.close()
        output.seek(0)

        filename = f"Vendor_Products_{datetime.now().strftime('%d_%m_%Y')}.xlsx"
        file_content = base64.b64encode(output.read())

        attachment = self.env['ir.attachment'].create({
            'name': filename,
            'datas': file_content,
            'type': 'binary',
            'mimetype': 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
        })

        return {
            'type': 'ir.actions.act_url',
            'url': f'/web/content/{attachment.id}?download=true&filename={filename}',
            'target': 'self'
        }
