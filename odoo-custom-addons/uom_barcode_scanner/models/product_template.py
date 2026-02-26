from odoo import models, fields, api
import re


class ProductTemplate(models.Model):
    _inherit = 'product.template'
    
    barcode_uom_ids = fields.One2many('product.barcode.uom', 'product_id', string="Barcode UoMs")
    barcode_count = fields.Integer(string="Barcode Count", compute='_compute_barcode_count', store=True)
    uom_category_id = fields.Many2one('uom.category', string='UoM Category', help='Filter available UoMs by category')
    nutrition_table_html = fields.Html("Nutrition Table", compute='_compute_nutrition_table')

    @api.depends('barcode_uom_ids', 'barcode_uom_ids.active')
    def _compute_barcode_count(self):
        for record in self:
            record.barcode_count = len(record.barcode_uom_ids.filtered('active'))
    
    def action_view_barcodes(self):
        self.ensure_one()
        action = {
            'name': 'Product Barcodes',
            'type': 'ir.actions.act_window',
            'res_model': 'product.barcode.uom',
            'view_mode': 'tree,form',
            'domain': [('product_id', '=', self.id)],
            'context': {
                'default_product_id': self.id,
                'search_default_product_id': self.id,
                'default_uom_category_id': self.uom_category_id.id if self.uom_category_id else False,
            },
        }
        return action

    @api.model
    def name_search(self, name='', args=None, operator='ilike', limit=100):
        args = args or []
        if name:
            # First check if it's a barcode from product.barcode.uom
            barcode_line = self.env['product.barcode.uom'].search([
                ('barcode', '=', name)
            ], limit=1)

            if barcode_line:
                # Return the product template
                product_template = barcode_line.product_id
                return product_template.name_get()

        return super().name_search(name=name, args=args, operator=operator, limit=limit)

    @api.depends('x_studio_nutrition')
    def _compute_nutrition_table(self):
        for record in self:
            if not record.x_studio_nutrition:
                record.nutrition_table_html = ''
                continue

            lines = [line.strip() for line in record.x_studio_nutrition.splitlines() if line.strip()]

            rows_html = ""
            for i, line in enumerate(lines, start=1):

                match = re.match(r'^(.*?\bper\s*\d*\s*\w*)\s+([\d.,]+\s*\w+)$', line, re.IGNORECASE)
                if not match:
                    match = re.match(r'^(.*?\D)\s+([\d.,]+\s*\w+(?:\s*\w+)*)$', line)

                if match:
                    label = match.group(1).strip()
                    value = match.group(2).strip()
                else:
                    label, value = line, ""

                rows_html += f"""
                    <tr>
                        <td style="padding:2px 6px; font-weight:500; border:none;">{label}</td>
                        <td style="padding:2px 6px; text-align:right; border:none;">{value}</td>
                    </tr>
                """
            record.nutrition_table_html = f"""
                <table border="1" style="border-collapse:collapse; width:100%; font-size:7.5px; 
                       font-family:Arial; table-layout:fixed; line-height:1.1;">
                    <thead>
                        <tr style="background:#f2f2f2;">
                            <th style="padding:1px 2px; text-align:left; width:68%; font-weight:bold;">Nutrient</th>
                            <th style="padding:1px 2px; text-align:right; width:32%; font-weight:bold;">Amount</th>
                        </tr>
                    </thead>
                    <tbody style="font-size:7.5px;">
                        {rows_html}
                    </tbody>
                </table>
            """

