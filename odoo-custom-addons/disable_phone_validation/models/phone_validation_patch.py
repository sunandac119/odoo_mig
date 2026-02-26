
from odoo import models
import re

class PhoneValidationMixinOverride(models.AbstractModel):
    _inherit = 'phone.validation.mixin'

    def phone_format(self, number, country=None, company=None):
        # Remove any non-digit characters, except leading +
        if number:
            number = re.sub(r'(?!^\+)\D', '', number)
        return number

    def _validate_phone(self, number, country_code=None):
        return number  # Skip validation

    def _normalize_phone(self, number, country_code=None):
        return number  # Skip normalization
