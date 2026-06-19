from odoo import api, fields, models


class ResBank(models.Model):
    _name = "res.bank"
    _inherit = ["res.bank", "dm.geodata.address.mixin"]

    # res.bank має власні адресні колонки, але використовує нестандартні m2o-імена
    # `state`/`country` (а не state_id/country_id), тож загальну логіку міксина на
    # боці власника спрямовуємо на них через мапу нижче. area/hromada — власні
    # (стандартні) поля міксина.
    _geodata_fields = {
        "country_id": "country",
        "state_id": "state",
        "city": "city",
        "street": "street",
        "street2": "street2",
        "zip": "zip",
        "area": "area",
        "hromada": "hromada",
    }

    # res.bank не має власного country_code; додаємо його для гейта view за країною.
    country_code = fields.Char(related="country.code")

    # Тонкі onchange-обгортки -> загальне тіло міксина (оголошені тут, бо імена
    # полів реальні на res.bank; міксин не повинен їх жорстко зашивати).
    @api.onchange("state")
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
