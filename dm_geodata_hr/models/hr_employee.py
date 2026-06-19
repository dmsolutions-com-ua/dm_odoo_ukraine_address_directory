from odoo import api, fields, models


class HrEmployee(models.Model):
    _name = "hr.employee"
    _inherit = ["hr.employee", "dm.geodata.address.mixin"]

    # hr.employee тримає домашню адресу у власних колонках `private_*` (без
    # делегування на res.partner в Odoo 19), тож загальну логіку міксина на боці
    # власника спрямовуємо на ці імена полів через мапу нижче. area/hromada —
    # власні (стандартні) поля міксина.
    _geodata_fields = {
        "country_id": "private_country_id",
        "state_id": "private_state_id",
        "city": "private_city",
        "street": "private_street",
        "street2": "private_street2",
        "zip": "private_zip",
        "area": "area",
        "hromada": "hromada",
    }

    # hr.employee не має власного country_code; додаємо його для гейта view за країною.
    country_code = fields.Char(related="private_country_id.code")

    # Тонкі onchange-обгортки -> загальне тіло міксина (оголошені тут, бо імена
    # полів реальні на hr.employee; міксин не повинен їх жорстко зашивати).
    @api.onchange("private_state_id")
    def _onchange_geodata_state(self):
        self._geodata_onchange("state_id")

    @api.onchange("area")
    def _onchange_geodata_area(self):
        self._geodata_onchange("area")

    @api.onchange("private_city")
    def _onchange_geodata_city(self):
        self._geodata_onchange("city")

    @api.onchange("private_street")
    def _onchange_geodata_street(self):
        self._geodata_onchange("street")
