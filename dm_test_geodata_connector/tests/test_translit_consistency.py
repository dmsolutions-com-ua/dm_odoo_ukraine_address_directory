from odoo.tests.common import TransactionCase


class TestTranslitConsistency(TransactionCase):
    """EN transliteration must stay in lock-step with the UA address on a REUSED
    record. Regression for: after several address changes the «Інформація про
    адресу» tab showed different UA vs EN addresses, and re-saving did not fix it
    (the stale `_en` survived and `address_full_en` recomputed from it). Since EN
    is a computed derivative of UA, a stale value is structurally impossible —
    these tests pin that guarantee down."""

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.credential = cls.env["dm.geodata.api.credential"].create({
            "name": "Translit Consistency",
            "api_url": "https://example.test",
            "api_username": "u",
            "api_password": "p",
        })
        cls.Geo = cls.env["dm.geodata.address"]

    # Явний шаблон замість дефолтного з credential — тест перевіряє транслітерацію,
    # а не поточний дефолт формату документа.
    _EN_TEMPLATE = "{Region}, {Area}, {City}, {StrType} {Street}, {HouseNum}"

    def test_stale_en_field_cleared_when_ua_omits_it(self):
        # Адреса A з районом -> area_en заповнене.
        addr = self.Geo.create({
            "region": "Львівська обл.", "area": "Личаківський р-н",
            "city": "Львів", "str_type": "вул.", "street": "Личаківська",
        })
        self.assertEqual(addr.area_en, "Lychakivskyi r-n")

        # Перемикаємось на адресу B БЕЗ району -> area_en має ОЧИСТИТИСЬ.
        addr.write({"area": False, "region": "Київ",
                    "city": "Київ", "street": "Хрещатик"})
        self.assertFalse(
            addr.area_en,
            "stale area_en from the previous address must be cleared",
        )
        self.assertEqual(addr.city_en, "Kyiv")

    def test_empty_ua_gives_empty_en(self):
        addr = self.Geo.create({
            "region": "Львівська обл.", "city": "Львів",
            "str_type": "вул.", "street": "Личаківська",
        })
        self.assertEqual(addr.city_en, "Lviv")

        addr.write({"region": False, "city": False,
                    "street": False, "str_type": False})
        self.assertFalse(addr.city_en)
        self.assertFalse(addr.street_en)
        self.assertFalse(addr.region_en)
        en_doc = addr._render_api_template(self._EN_TEMPLATE, "en")
        self.assertNotIn("Lviv", en_doc,
                         "EN of the previous address must not persist")
        self.assertNotIn("Lychakivska", en_doc)

    def test_ua_and_en_consistent_after_switch(self):
        # Наскрізно: після зміни адреси документні UA та EN описують ОДНУ адресу,
        # без залишків попередньої.
        addr = self.Geo.create({
            "region": "Львівська обл.", "city": "Львів",
            "str_type": "вул.", "street": "Личаківська", "house_num": "5",
        })
        addr.write({
            "region": "Київ", "city": "Київ",
            "str_type": "вул.", "street": "Хрещатик", "house_num": "1",
        })
        en_doc = addr._render_api_template(self._EN_TEMPLATE, "en")
        self.assertIn("Kyiv", en_doc)
        self.assertIn("Khreshchatyk", en_doc)
        self.assertNotIn("Lviv", en_doc)
        self.assertNotIn("Lychakivska", en_doc)

    def test_clear_down_drops_en_of_lower_levels(self):
        # Перевибір міста чистить вулицю/будинок (clear-down) — EN зникає разом.
        addr = self.Geo.create_from_api({
            "Id": 1, "City": "Львів", "SettlementType": "місто",
            "Street": "Личаківська", "StrType": "вул.",
            "HouseNum": "5", "HouseNumAdd": "Б",
        })
        self.assertEqual(addr.street_en, "Lychakivska")
        self.assertEqual(addr.house_num_add_en, "B")

        addr.update_from_api({"Id": 2, "City": "Київ", "SettlementType": "місто"})
        self.assertFalse(addr.street_en)
        self.assertFalse(addr.str_type_en)
        self.assertFalse(addr.house_num_add_en)
        self.assertEqual(addr.city_en, "Kyiv")
