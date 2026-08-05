from odoo.tests.common import TransactionCase


class TestNewRecordDefaults(TransactionCase):
    """Поля-налаштування на формі НОВОГО запису.

    Клієнт наповнює нову форму не через `read`, а першим викликом `onchange`, і
    той засіває КОЖНЕ поле форми без `default` значенням False прямо в кеш
    нового запису (web/models/models.py, гілка `first_call`). Обчислюване поле
    без @api.depends після цього вже не перераховується, тож на новій картці
    висів банер «Geodata.online not configured» попри налаштований credential.
    """

    # Мінімальний зріз того, що клієнт шле у fields_spec форми контакту.
    _SPEC = {
        "name": {},
        "city": {},
        "country_id": {},
        "has_geodata_credential": {},
        "geodata_show_manual_hint": {},
    }

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.credential = cls.env["dm.geodata.api.credential"].create({
            "name": "New Record Defaults",
            "api_url": "https://example.test",
            "api_username": "u",
            "api_password": "p",
        })

    def _first_onchange(self):
        """Рівно той виклик, який робить веб-клієнт на «Новий контакт»."""
        return self.env["res.partner"].onchange({}, [], self._SPEC)["value"]

    def test_new_contact_sees_configured_credential(self):
        values = self._first_onchange()
        self.assertTrue(values["has_geodata_credential"])
        self.assertTrue(values["geodata_show_manual_hint"])

    def test_new_contact_follows_manual_hint_switch(self):
        # Вимикач на credential мусить діяти і до збереження картки.
        self.credential.show_manual_hint = False
        self.assertFalse(self._first_onchange()["geodata_show_manual_hint"])

    def test_new_contact_without_credential_shows_warning(self):
        # Банер має лишатися чесним: без активного credential — показуємо.
        self.env["dm.geodata.api.credential"].search([]).active = False
        self.assertFalse(self._first_onchange()["has_geodata_credential"])

    def test_saved_contact_keeps_computed_value(self):
        # Збережений запис іде шляхом compute — він і далі має бути правильним.
        partner = self.env["res.partner"].create({"name": "Saved"})
        self.assertTrue(partner.has_geodata_credential)
        self.assertTrue(partner.geodata_show_manual_hint)
