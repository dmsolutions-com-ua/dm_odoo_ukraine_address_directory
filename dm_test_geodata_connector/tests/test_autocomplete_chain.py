from odoo.tests.common import TransactionCase


class TestAutocompleteChain(TransactionCase):
    """City -> Street -> House chain using CityString/StreetString/HouseString
    and the st_moniker/house_moniker chain (tests #3-#7), merging into ONE
    dm.geodata.address (test #8), plus the one-line full-address search (#9)."""

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.env["ir.config_parameter"].sudo().set_param("geodata.test.mock_api", "1")
        cls.env["dm.geodata.api.credential"].create({
            "name": "Chain Mock Cred",
            "api_url": "https://example.test",
            "api_username": "u",
            "api_password": "p",
        })
        cls.P = cls.env["res.partner"]
        cls.UA = {"country_code": "UA"}

    def test_full_chain_single_address(self):
        # 1) Підказка міста (мітка з CityString)
        cities = self.P.geodata_autocomplete_cities("Київ", self.UA)
        self.assertTrue(cities)
        self.assertEqual(cities[0]["label"], "місто Київ, Київська обл.")

        # 2) Застосувати місто -> отримуємо id адреси + moniker міста + визначену область (#2)
        res_city = self.P.apply_address(False, cities[0]["data"])
        addr_id = res_city["geodata_address_id"]["id"]
        self.assertTrue(addr_id)
        self.assertEqual(res_city["geodata_city_moniker"], "mock-city-moniker-kyiv")
        self.assertTrue(res_city.get("state_id"), "Region must resolve to a state (#2)")

        # 3) Підказка вулиці за moniker міста (мітка з StreetString)
        dep = dict(self.UA, geodata_city_moniker="mock-city-moniker-kyiv")
        streets = self.P.geodata_autocomplete_streets("Хрещатик", dep)
        self.assertTrue(streets)
        self.assertEqual(streets[0]["label"], "вул. Хрещатик")

        # 4) Застосувати вулицю -> зливається в ТУ САМУ адресу; отримуємо moniker вулиці
        res_street = self.P.apply_address(False, streets[0]["data"], addr_id)
        self.assertEqual(res_street["geodata_address_id"]["id"], addr_id)
        self.assertEqual(res_street["geodata_street_moniker"], "mock-street-moniker")

        # 5) Підказка будинку: номер після мітки ВИБРАНОЇ вулиці, береться
        #    з пов'язаної dm.geodata.address (не із сирого вмісту поля) — #4.
        dep_h = dict(
            self.UA,
            geodata_city_moniker="mock-city-moniker-kyiv",
            geodata_street_moniker="mock-street-moniker",
            geodata_address_id=addr_id,
        )
        houses = self.P.geodata_autocomplete_streets("вул. Хрещатик 1", dep_h)
        self.assertTrue(houses)
        # Мітка = StreetString (geo.street_string) + ", " + HouseString.
        self.assertEqual(houses[0]["label"], "вул. Хрещатик, 1")

        # 6) Застосувати будинок -> усе та сама адреса, тепер із номером будинку
        self.P.apply_address(False, houses[0]["data"], addr_id)
        addr = self.env["dm.geodata.address"].browse(addr_id)
        self.assertEqual(addr.city, "Київ")
        self.assertEqual(addr.street, "Хрещатик")
        self.assertEqual(addr.house_num, "1")

    def test_house_routing_ignores_old_paren(self):
        # Поле вулиці з "(старою назвою)" не має ламати маршрутизацію будинків.
        cities = self.P.geodata_autocomplete_cities("Київ", self.UA)
        addr_id = self.P.apply_address(False, cities[0]["data"])["geodata_address_id"]["id"]
        dep = dict(self.UA, geodata_city_moniker="mock-city-moniker-kyiv")
        streets = self.P.geodata_autocomplete_streets("Хрещатик", dep)
        self.P.apply_address(False, streets[0]["data"], addr_id)
        dep_h = dict(
            self.UA,
            geodata_city_moniker="mock-city-moniker-kyiv",
            geodata_street_moniker="mock-street-moniker",
            geodata_address_id=addr_id,
        )
        houses = self.P.geodata_autocomplete_streets(
            "вул. Хрещатик (вул. Стара) 1", dep_h)
        self.assertTrue(houses, "House routing must ignore the (old name) parenthetical")
        self.assertEqual(houses[0]["label"], "вул. Хрещатик, 1")

    def test_house_label_combines_streetstring(self):
        # Мітка = StreetString + HouseString; StreetString використовується як є, тож
        # історична назва в дужках (сформована API) лишається, незалежно від
        # налаштування show_old_names.
        res = self.P._format_house_suggestion(
            {"HouseString": "1"}, "вул. Шевченка (вул. Стара)")
        self.assertEqual(res["label"], "вул. Шевченка (вул. Стара), 1")
        # Немає street string -> голий HouseString.
        self.assertEqual(self.P._format_house_suggestion({"HouseString": "8Б"})["label"], "8Б")

    def test_streets_need_city_moniker(self):
        # Без moniker міста пошук вулиць нічого не повертає (корінь test #3).
        self.assertEqual(self.P.geodata_autocomplete_streets("Хрещатик", self.UA), [])

    def test_full_address_search(self):
        res = self.P.geodata_autocomplete_full_address("Київ Хрещатик 1", self.UA)
        self.assertTrue(res)
        self.assertEqual(res[0]["label"], "місто Київ, вул. Хрещатик, 1Б")
        applied = self.P.apply_address(False, res[0]["data"])
        self.assertEqual(applied.get("city"), "місто Київ")
        self.assertTrue(applied["geodata_address_id"]["id"])
