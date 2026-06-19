from odoo.tests.common import TransactionCase


class TestAddressFields(TransactionCase):
    """Full API field storage + correct building/settlement coordinates (v1.4)."""

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.env["ir.config_parameter"].sudo().set_param("geodata.test.mock_api", "1")
        cls.env["dm.geodata.api.credential"].create({
            "name": "Fields Mock Cred",
            "api_url": "https://example.test",
            "api_username": "u",
            "api_password": "p",
        })
        cls.P = cls.env["res.partner"]
        cls.UA = {"country_code": "UA"}

    def test_city_stores_all_fields_and_settlement_coords(self):
        cities = self.P.geodata_autocomplete_cities("Київ", self.UA)
        res = self.P.apply_address(False, cities[0]["data"])
        addr = self.env["dm.geodata.address"].browse(res["geodata_address_id"]["id"])
        # Усі отримані поля API зберігаються (вкл. передмістя / старі назви / string).
        self.assertEqual(addr.suburb, "Печерськ")
        self.assertEqual(addr.hromada_old, "Стара громада")
        self.assertEqual(addr.settlement_type_old, "містечко")
        self.assertEqual(addr.city_string, "місто Київ, Київська обл.")
        # Payload міста (без вулиці/будинку) -> координати йдуть НАСЕЛЕНОМУ ПУНКТУ, не будинку.
        self.assertAlmostEqual(addr.latitude_settlement, 50.450412, places=4)
        self.assertFalse(addr.latitude, "Building latitude must stay empty for a city")

    def test_house_sets_building_coords_keeps_settlement(self):
        cities = self.P.geodata_autocomplete_cities("Київ", self.UA)
        res = self.P.apply_address(False, cities[0]["data"])
        addr_id = res["geodata_address_id"]["id"]
        # Застосовуємо payload будинку (злиття в ту саму адресу).
        from odoo.addons.dm_test_geodata_connector.models.geodata_api_mock import _MOCK_HOUSE
        self.P.apply_address(False, dict(_MOCK_HOUSE), addr_id)
        addr = self.env["dm.geodata.address"].browse(addr_id)
        # Координати будинку тепер виставлені з будинку...
        self.assertAlmostEqual(addr.latitude, 50.4501, places=4)
        # ...а координати населеного пункту з кроку міста збережено (#4).
        self.assertAlmostEqual(addr.latitude_settlement, 50.450412, places=4)
        # Поля метро збережено.
        self.assertEqual(addr.metro_station, "Золоті ворота")
