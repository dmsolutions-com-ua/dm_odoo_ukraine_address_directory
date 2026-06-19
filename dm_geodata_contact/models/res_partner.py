from odoo import api, models


class ResPartner(models.Model):
    _name = "res.partner"
    _inherit = ["res.partner", "dm.geodata.address.mixin"]

    # res.partner використовує стандартні імена адресних полів, тож типова мапа
    # `_geodata_fields` з міксина підходить як є. Загальна логіка на боці власника
    # (clear-down, відв'язування/пониження, верифікація, синк при записі, поля
    # area/hromada) — у dm.geodata.address.mixin; тут лишаємо лише специфічне для
    # партнера.

    @api.model
    def default_get(self, fields_list):
        res = super().default_get(fields_list)
        if "country_id" in fields_list and not res.get("country_id"):
            ukraine = self.env.ref("base.ua", raise_if_not_found=False)
            if ukraine:
                res["country_id"] = ukraine.id
        return res

    # Тонкі onchange-обгортки -> загальне тіло міксина (оголошені тут, бо імена
    # полів реальні на res.partner; міксин не повинен їх жорстко зашивати).
    @api.onchange("country_id")
    def _onchange_geodata_country(self):
        # Зміна країни в адресному блоці теж робить «Пошук адреси» неактуальним.
        self.geodata_search = False

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
