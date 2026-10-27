from odoo import api, fields, models

_HR_USER = "hr.group_hr_user"


class HrEmployee(models.Model):
    _name = "hr.employee"
    _inherit = ["hr.employee", "dm.geodata.address.mixin"]

    # hr.employee в Odoo 18 тримає домашню адресу у власних колонках `private_*`
    # (без делегування), тож загальну логіку міксина на боці власника спрямовуємо
    # на ці імена полів через мапу нижче. area/hromada — власні (стандартні)
    # поля міксина.
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
    country_code = fields.Char(related="private_country_id.code", groups=_HR_USER)

    # Домашня адреса працівника — приватні дані, як і стандартні `private_*`.
    # Без `groups` збережені поля міксина потрапляють у prefetch будь-якого
    # звертання до hr.employee, а для некадрового користувача Odoo читає лише
    # поля hr.employee.public -> AccessError «not available for employee public
    # profiles» (напр. при плануванні зустрічі з ліда). Тут лише додаємо groups,
    # решта атрибутів успадковується з визначення в міксині.
    geodata_address_id = fields.Many2one(groups=_HR_USER)
    geodata_autocomplete_active = fields.Boolean(groups=_HR_USER)
    geodata_city_moniker = fields.Char(groups=_HR_USER)
    geodata_street_moniker = fields.Char(groups=_HR_USER)
    geodata_search = fields.Char(groups=_HR_USER)
    has_geodata_credential = fields.Boolean(groups=_HR_USER)
    geodata_show_manual_hint = fields.Boolean(groups=_HR_USER)
    geodata_city_verified = fields.Boolean(groups=_HR_USER)
    geodata_street_verified = fields.Boolean(groups=_HR_USER)
    geodata_house_verified = fields.Boolean(groups=_HR_USER)
    geodata_zip_verified = fields.Boolean(groups=_HR_USER)
    geodata_verified_level = fields.Char(groups=_HR_USER)
    geodata_address_full_ua = fields.Char(groups=_HR_USER)
    geodata_address_full_en = fields.Char(groups=_HR_USER)
    geodata_address_letter_ua = fields.Char(groups=_HR_USER)
    geodata_address_letter_en = fields.Char(groups=_HR_USER)
    geodata_address_display = fields.Char(groups=_HR_USER)
    geodata_details_col1 = fields.Html(groups=_HR_USER)
    geodata_details_col2 = fields.Html(groups=_HR_USER)
    geodata_kato = fields.Char(groups=_HR_USER)
    geodata_koatuu = fields.Char(groups=_HR_USER)
    geodata_terr_status = fields.Char(groups=_HR_USER)
    geodata_address_updated = fields.Datetime(groups=_HR_USER)
    area = fields.Char(groups=_HR_USER)
    hromada = fields.Char(groups=_HR_USER)

    # Тонкі onchange-обгортки -> загальне тіло міксина (оголошені тут, бо імена
    # полів реальні на hr.employee; міксин не повинен їх жорстко зашивати).
    @api.onchange("private_country_id")
    def _onchange_geodata_country(self):
        self._geodata_onchange("country_id")

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
