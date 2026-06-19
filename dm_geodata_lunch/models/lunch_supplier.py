from odoo import api, fields, models


class LunchSupplier(models.Model):
    _name = "lunch.supplier"
    _inherit = ["lunch.supplier", "dm.geodata.address.mixin"]

    # lunch.supplier тримає адресу на related-полях до partner_id
    # (street/street2/city/state_id/country_id), але поле поштового індексу зветься
    # `zip_code` (related до partner.zip), а не `zip`. Перевизначаємо мапу лише для
    # цієї відмінності; решта рівнів — стандартні. Постачальник володіє власним
    # зв'язком dm.geodata.address (1:1); текст адреси спільний з його партнером
    # через related+inverse.
    _geodata_fields = {
        "country_id": "country_id", "state_id": "state_id",
        "city": "city", "street": "street", "street2": "street2",
        "zip": "zip_code",
        "area": "area", "hromada": "hromada",
    }

    # lunch.supplier не має власного country_code; додаємо його для гейта view за
    # країною (форма використовує `country_code != 'UA'` і приховане поле country_code),
    # як у res.company / crm.lead.
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
