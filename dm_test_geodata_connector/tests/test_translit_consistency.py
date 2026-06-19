from unittest.mock import patch

from odoo.tests.common import TransactionCase


class TestTranslitConsistency(TransactionCase):
    """EN transliteration must stay in lock-step with the UA address on a REUSED
    record. Regression for: after several address changes the «Інформація про
    адресу» tab showed different UA vs EN addresses, and re-saving did not fix it
    (the stale `_en` survived and `address_full_en` recomputed from it)."""

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.credential = cls.env["dm.geodata.api.credential"].create({
            "name": "Translit Consistency",
            "api_url": "https://example.test",
            "api_username": "u",
            "api_password": "p",
            "store_english": True,
        })
        cls.Geo = cls.env["dm.geodata.address"]

    def _fetch_en(self, addr, en_response):
        """Run fetch_en_translit with a controlled EN api_address response."""
        with patch.object(type(self.credential), "api_address",
                          return_value=en_response):
            addr.fetch_en_translit(self.credential)

    def test_stale_en_field_cleared_when_new_response_omits_it(self):
        # Адреса A з районом -> area_en заповнене.
        addr = self.Geo.create({
            "region": "Львівська обл.", "area": "Личаківський р-н",
            "city": "Львів", "str_type": "вул.", "street": "Личаківська",
        })
        self._fetch_en(addr, [{
            "Region": "Lvivska obl.", "Area": "Lychakivskyi r-n",
            "City": "Lviv", "Street": "Lychakivska", "StrType": "vul.",
        }])
        self.assertEqual(addr.area_en, "Lychakivskyi r-n")

        # Перемикаємось на адресу B БЕЗ району (UA оновлено), а EN-відповідь B не
        # містить Area -> area_en має ОЧИСТИТИСЬ, а не лишитись від A.
        addr.write({"area": False, "region": "Київ",
                    "city": "Київ", "street": "Хрещатик"})
        self._fetch_en(addr, [{
            "Region": "Kyiv", "City": "Kyiv",
            "Street": "Khreshchatyk", "StrType": "vul.",
        }])
        self.assertFalse(
            addr.area_en,
            "stale area_en from the previous address must be cleared",
        )
        self.assertEqual(addr.city_en, "Kyiv")

    def test_empty_en_response_clears_and_falls_back_to_ua(self):
        # Адреса A з повним EN.
        addr = self.Geo.create({
            "region": "Львівська обл.", "city": "Львів",
            "str_type": "вул.", "street": "Личаківська",
        })
        self._fetch_en(addr, [{
            "Region": "Lvivska obl.", "City": "Lviv",
            "Street": "Lychakivska", "StrType": "vul.",
        }])
        self.assertEqual(addr.city_en, "Lviv")

        # Нова адреса B, але EN-запит ПОРОЖНІЙ (збій/немає збігу/тротлінг).
        addr.write({"region": "Київ", "city": "Київ", "street": "Хрещатик"})
        self._fetch_en(addr, [])

        # Усі _en очищено -> EN не показує стару адресу A; падає на UA (кирилиця).
        self.assertFalse(addr.city_en)
        self.assertFalse(addr.street_en)
        en_doc = addr._format_full_address("en")
        self.assertNotIn("Lviv", en_doc,
                         "EN of the previous address must not persist")
        self.assertNotIn("Lychakivska", en_doc)
        self.assertIn("Київ", en_doc)  # UA-fallback тієї ж адреси

    def test_ua_and_en_consistent_after_switch(self):
        # Наскрізно: після зміни адреси документні UA та EN збігаються (та сама
        # адреса), без залишків попередньої.
        addr = self.Geo.create({
            "region": "Львівська обл.", "city": "Львів",
            "str_type": "вул.", "street": "Личаківська", "house_num": "5",
        })
        self._fetch_en(addr, [{
            "Region": "Lvivska obl.", "City": "Lviv",
            "Street": "Lychakivska", "StrType": "vul.",
        }])
        addr.write({
            "region": "Київ", "city": "Київ",
            "str_type": "вул.", "street": "Хрещатик", "house_num": "1",
        })
        self._fetch_en(addr, [{
            "Region": "Kyiv", "City": "Kyiv",
            "Street": "Khreshchatyk", "StrType": "vul.",
        }])
        en_doc = addr._format_full_address("en")
        # Нова адреса в EN, жодного сегмента попередньої.
        self.assertIn("Kyiv", en_doc)
        self.assertIn("Khreshchatyk", en_doc)
        self.assertNotIn("Lviv", en_doc)
        self.assertNotIn("Lychakivska", en_doc)
