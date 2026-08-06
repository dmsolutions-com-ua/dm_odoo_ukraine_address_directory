from odoo.tests.common import TransactionCase


class TestCountryGate(TransactionCase):
    """Гейт країни для пошуку підказок (`_geodata_form_country_is_ua`).

    Явно вказана країна вирішує все сама; ПОРОЖНЯ країна на формі трактується
    за країною компанії. Це шлях `crm.lead` (і будь-якого власника з аліаса чи
    імпорту), де країни за замовчуванням немає — на відміну від `res.partner`,
    якому її ставить `default_get`.
    """

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.env["ir.config_parameter"].sudo().set_param("geodata.test.mock_api", "1")
        cls.env["dm.geodata.api.credential"].create({
            "name": "Country Gate Mock Cred",
            "api_url": "https://example.test",
            "api_username": "u",
            "api_password": "p",
        })
        cls.P = cls.env["res.partner"]
        cls.ua = cls.env.ref("base.ua")
        cls.foreign = cls.env.ref("base.fr")

    def _set_company_country(self, country):
        self.env.company.country_id = country

    # --- явно вказана країна: рішення не залежить від компанії ---------------

    def test_explicit_ua_allowed_on_foreign_company(self):
        self._set_company_country(self.foreign)
        self.assertTrue(self.P.geodata_autocomplete_cities("Київ", {"country_code": "UA"}))
        self.assertTrue(
            self.P.geodata_autocomplete_cities("Київ", {"country_id": self.ua.id}))

    def test_explicit_foreign_blocked_on_ua_company(self):
        self._set_company_country(self.ua)
        self.assertEqual(
            self.P.geodata_autocomplete_cities("Київ", {"country_code": "FR"}), [])
        self.assertEqual(
            self.P.geodata_autocomplete_cities("Київ", {"country_id": self.foreign.id}), [])

    # --- порожня країна: вирішує країна компанії ----------------------------

    def test_empty_country_allowed_on_ua_company(self):
        # Саме цей випадок робив підказки німими на новій нагоді CRM.
        self._set_company_country(self.ua)
        for dep in ({"country_code": ""}, {}, None):
            self.assertTrue(
                self.P.geodata_autocomplete_cities("Київ", dep),
                "Порожня країна на українській компанії має дозволяти пошук: %r" % (dep,))

    def test_empty_country_blocked_on_foreign_company(self):
        self._set_company_country(self.foreign)
        for dep in ({"country_code": ""}, {}, None):
            self.assertEqual(
                self.P.geodata_autocomplete_cities("Київ", dep), [],
                "Порожня країна на іноземній компанії не має витрачати виклики API")

    def test_empty_country_blocked_without_company_country(self):
        self._set_company_country(self.env["res.country"])
        self.assertEqual(self.P.geodata_autocomplete_cities("Київ", {}), [])

    # --- гейт однаковий для всіх точок входу --------------------------------

    def test_gate_applies_to_streets_and_full_address(self):
        self._set_company_country(self.foreign)
        dep = {"geodata_city_moniker": "mock-city-moniker-kyiv"}
        self.assertEqual(self.P.geodata_autocomplete_streets("Хрещатик", dep), [])
        self.assertEqual(self.P.geodata_autocomplete_full_address("Київ Хрещатик", {}), [])
        self._set_company_country(self.ua)
        self.assertTrue(self.P.geodata_autocomplete_streets("Хрещатик", dep))
        self.assertTrue(self.P.geodata_autocomplete_full_address("Київ Хрещатик", {}))
