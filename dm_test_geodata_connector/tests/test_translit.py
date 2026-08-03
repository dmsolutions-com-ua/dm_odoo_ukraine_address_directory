from unittest.mock import patch

from odoo.tests.common import TransactionCase


class TestTransliterationAndRawPayload(TransactionCase):
    """EN transliteration is computed locally for ALL `_en` fields (incl. the
    house suffix, settlement district and old names) with no API call, and the
    raw API payload must be kept verbatim (store everything, no excs)."""

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.env["ir.config_parameter"].sudo().set_param("geodata.test.mock_api", "1")
        cls.credential = cls.env["dm.geodata.api.credential"].create({
            "name": "Translit Mock",
            "api_url": "https://example.test",
            "api_username": "u",
            "api_password": "p",
        })
        cls.Geo = cls.env["dm.geodata.address"]

    def _full_address(self):
        return self.Geo.create({
            "city": "Київ", "settlement_type": "місто",
            "city_district": "Шевченківський",
            "str_type": "вул.", "street": "Хрещатик",
            "house_num": "1", "house_num_add": "Б",
        })

    def test_en_translit_captures_all_fields(self):
        addr = self._full_address()
        self.assertEqual(addr.house_num_add_en, "B")
        self.assertEqual(addr.city_district_en, "Shevchenkivskyi")
        self.assertEqual(addr.city_en, "Kyiv")
        self.assertEqual(addr.settlement_type_en, "misto")
        self.assertEqual(addr.street_en, "Khreshchatyk")
        self.assertEqual(addr.str_type_en, "vul.")

    def test_en_translit_covers_every_mapped_field(self):
        # Жодна UA-колонка з мапи не лишається без EN-двійника.
        vals = {ua: "Згорани" for ua, _en in self.Geo._TRANSLIT_FIELDS}
        addr = self.Geo.create(vals)
        for _ua_field, en_field in self.Geo._TRANSLIT_FIELDS:
            with self.subTest(field=en_field):
                self.assertEqual(addr[en_field], "Zghorany")

    def test_en_translit_needs_no_api_call(self):
        # Транслітерація локальна: будь-яке звернення до API тут — регресія.
        def _boom(*args, **kwargs):
            raise AssertionError("transliteration must not call the API")

        with patch.object(type(self.credential), "_api_request", _boom):
            addr = self._full_address()
            self.assertEqual(addr.city_en, "Kyiv")
            self.assertEqual(addr._render_api_template("{Street}", "en"),
                             "Khreshchatyk")

    def test_en_house_string_uses_translit_suffix(self):
        addr = self._full_address()
        result = addr._render_api_template(
            "{StrType} {Street}, {HouseNum}{HouseNumAdd}", "en")
        self.assertEqual(result, "vul. Khreshchatyk, 1B")
        self.assertNotIn("Б", result, "Cyrillic house suffix must not leak into EN")

    def test_en_cleared_with_its_ua_source(self):
        # EN — computed від UA, тож очищення UA прибирає й EN у тому ж write.
        addr = self._full_address()
        addr.write({"street": False, "str_type": False})
        self.assertFalse(addr.street_en)
        self.assertFalse(addr.str_type_en)

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
        # EN не приходить з API — його дає локальна транслітерація.
        self.assertEqual(addr.street_en, "Khreshchatyk")
