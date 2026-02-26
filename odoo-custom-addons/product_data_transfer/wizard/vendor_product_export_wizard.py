from odoo import models, fields

class VendorProductExportWizard(models.TransientModel):
    _name = "vendor.product.export.wizard"
    _description = "Export Vendor Products Wizard"

    vendor_ids = fields.Many2many('res.partner', string="Vendors")

    def action_download_excel(self):
        if not self.vendor_ids:
            raise UserError("Please select at least one vendor.")
        return self.vendor_ids.action_export_vendor_products_xlsx()
