from odoo import api, fields, models


class CrmLead(models.Model):
    _name = "crm.lead"
    _inherit = ["crm.lead", "dm.geodata.address.mixin"]

    # crm.lead використовує стандартні імена адресних полів, тож типова мапа
    # `_geodata_fields` з міксина підходить як є. Тут оголошуємо лише тонкі
    # onchange-обгортки (міксин не повинен жорстко зашивати імена полів).

    # crm.lead не має власного country_code; додаємо його для гейта view за країною.
    country_code = fields.Char(related="country_id.code")

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
