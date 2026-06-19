from odoo.tests.common import TransactionCase


class TestQueryNormalize(TransactionCase):
    """Space keystrokes and short queries must not trigger API calls; the
    trimmed query is what matters (AUDIT #17)."""

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.env["ir.config_parameter"].sudo().set_param("geodata.test.mock_api", "1")
        cls.env["dm.geodata.api.credential"].create({
            "name": "Mock Cred",
            "api_url": "https://example.test",
            "api_username": "u",
            "api_password": "p",
        })

    def test_normalize_collapses_spaces(self):
        Cred = self.env["dm.geodata.api.credential"]
        self.assertEqual(Cred._normalize_query("  Київ   вул.  "), "Київ вул.")
        self.assertEqual(Cred._normalize_query("Київ "), "Київ")

    _UA = {"country_code": "UA"}

    def test_cities_below_min_chars(self):
        # "Ки" (2 символи) і кінцевий пробіл нижче min_chars -> без результату.
        P = self.env["res.partner"]
        self.assertEqual(P.geodata_autocomplete_cities("Ки", self._UA), [])
        self.assertEqual(P.geodata_autocomplete_cities("Ки ", self._UA), [])

    def test_cities_returns_mock(self):
        res = self.env["res.partner"].geodata_autocomplete_cities("Київ", self._UA)
        self.assertTrue(res)
        self.assertEqual(res[0]["data"]["City"], "Київ")
        # Мітка має братися з CityString (test #5).
        self.assertEqual(res[0]["label"], "місто Київ, Київська обл.")

    def test_trailing_space_same_trimmed_query(self):
        P = self.env["res.partner"]
        a = P.geodata_autocomplete_cities("Київ", self._UA)
        b = P.geodata_autocomplete_cities("Київ ", self._UA)
        # Сервер нормалізує -> ідентичний набір результатів (немає окремого запиту "Київ ").
        self.assertEqual(a, b)

    def test_country_gate(self):
        # Без пошуку, якщо країна не Україна (test #1).
        P = self.env["res.partner"]
        self.assertEqual(P.geodata_autocomplete_cities("Київ", {"country_code": "FR"}), [])
        self.assertEqual(P.geodata_autocomplete_cities("Київ", {}), [])
