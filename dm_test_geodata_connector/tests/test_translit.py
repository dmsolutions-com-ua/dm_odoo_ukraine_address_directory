from odoo.tests.common import TransactionCase


class TestTransliterationAndRawPayload(TransactionCase):
    """EN transliteration must capture ALL `_en` fields (incl. the house suffix),
    and the raw API payload must be kept verbatim (store everything, no excs)."""

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.env["ir.config_parameter"].sudo().set_param("geodata.test.mock_api", "1")
        cls.credential = cls.env["dm.geodata.api.credential"].create({
            "name": "Translit Mock",
            "api_url": "https://example.test",
            "api_username": "u",
            "api_password": "p",
            "store_english": True,
        })
        cls.Geo = cls.env["dm.geodata.address"]

    def _full_address(self):
        return self.Geo.create({
            "city": "Київ", "settlement_type": "місто",
            "str_type": "вул.", "street": "Хрещатик",
            "house_num": "1", "house_num_add": "Б",
        })

    def test_en_translit_captures_all_fields(self):
        addr = self._full_address()
        addr.fetch_en_translit(self.credential)
        # Включно з полями, які раніше відкидались:
        self.assertEqual(addr.house_num_add_en, "b")
        self.assertEqual(addr.city_district_en, "Shevchenkivskyi")
        # ...і тими, що вже захоплювались раніше:
        self.assertEqual(addr.city_en, "Kyiv")
        self.assertEqual(addr.street_en, "Khreshchatyk")
        self.assertEqual(addr.str_type_en, "vul.")

    def test_en_house_string_uses_translit_suffix(self):
        addr = self._full_address()
        addr.fetch_en_translit(self.credential)
        result = addr._format_full_address("en")
        self.assertIn("vul. Khreshchatyk, 1b", result)
        self.assertNotIn("Б", result, "Cyrillic house suffix must not leak into EN")

    def test_raw_payload_kept_verbatim(self):
        # Null і недокументовані ключі мають лишитися недоторканими.
        raw = {"Id": 1, "City": "Київ", "SettlementType": "місто",
               "Suburb": None, "FutureUndocumentedField": "keep-me"}
        addr = self.Geo.create_from_api(raw)
        self.assertEqual(addr.api_payload["ua"]["FutureUndocumentedField"], "keep-me")
        self.assertIn("Suburb", addr.api_payload["ua"])  # null preserved
        # Злиття ланцюга: ключі вулиці додано без втрати ключів міста.
        addr.update_from_api({"StreetId": 50, "Street": "Хрещатик", "StreetType": "вул."})
        self.assertEqual(addr.api_payload["ua"]["City"], "Київ")
        self.assertEqual(addr.api_payload["ua"]["Street"], "Хрещатик")
        # EN-кошик заповнено транслітерацією.
        addr.fetch_en_translit(self.credential)
        self.assertEqual(addr.api_payload["en"]["City"], "Kyiv")
