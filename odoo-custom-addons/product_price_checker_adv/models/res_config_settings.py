from odoo import api, fields, models

class ResConfigSettings(models.TransientModel):
    _inherit = 'res.config.settings'

    checker_pricelist_id = fields.Many2one('product.pricelist', string='Checker Price List', help="Checker Price List.")

    @api.model
    def set_values(self):
        super(ResConfigSettings, self).set_values()
        IrDefault = self.env['ir.default'].sudo()
        IrDefault.set('res.config.settings', "checker_pricelist_id", self.checker_pricelist_id.id)

    @api.model
    def get_values(self):
        res = super(ResConfigSettings, self).get_values()
        IrDefault = self.env['ir.default'].sudo()
        checker_pricelist_id = IrDefault.get('res.config.settings', "checker_pricelist_id")

        res.update(
            checker_pricelist_id=checker_pricelist_id if checker_pricelist_id else False,
        )
        return res
