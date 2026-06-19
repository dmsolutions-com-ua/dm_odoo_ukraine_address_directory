from odoo import api, fields, models


class ResCompany(models.Model):
    _name = "res.company"
    _inherit = ["res.company", "dm.geodata.address.mixin"]

    # res.company використовує стандартні імена адресних полів (compute/inverse до
    # partner_id), тож типова мапа `_geodata_fields` з міксина підходить як є.
    # Компанія володіє власним зв'язком dm.geodata.address (1:1); текст адреси
    # спільний з її партнером через стандартні inverse-записи.

    # res.company не має власного country_code; додаємо його для гейта view за
    # країною (форма використовує `country_code != 'UA'` і приховане поле country_code).
    country_code = fields.Char(related="country_id.code")

    def _geodata_company_id(self):
        # Компанія володіє своєю адресою; прив'язуємо її до самої себе (res.company
        # не має поля `company_id`, тож загальний хук міксина зробив би її глобальною).
        self.ensure_one()
        return self.id

    @api.onchange("state_id")
    def _onchange_geodata_state(self):
        self._geodata_onchange("state_id")

    @api.onchange("area")
    def _onchange_geodata_area(self):
        self._geodata_onchange("area")

    @api.onchange("city")
    def _onchange_geodata_city(self):
        self._geodata_onchange("city")

    @api.onchange("street")
    def _onchange_geodata_street(self):
        self._geodata_onchange("street")
