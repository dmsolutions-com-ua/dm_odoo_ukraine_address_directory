from odoo.tests.common import TransactionCase


class TestIngestionNoDedup(TransactionCase):
    """Strict 1:1 model: create_from_api must NEVER deduplicate/reuse a row, and
    must never perform HTTP (AUDIT #5)."""

    def test_create_from_api_never_dedups(self):
        Address = self.env["dm.geodata.address"]
        api_data = {
            "ID": 555001, "City": "Львів", "Street": "Ринок",
            "HouseNum": "1", "Index_8x": "79000", "Region": "Львівська",
        }
        first = Address.create_from_api(api_data)
        second = Address.create_from_api(dict(api_data))
        self.assertNotEqual(
            first.id, second.id,
            "Identical payloads must create two distinct rows (no dedup)",
        )

    def test_create_from_api_adds_a_row_each_call(self):
        Address = self.env["dm.geodata.address"]
        before = Address.search_count([])
        Address.create_from_api({"ID": 555002, "City": "Одеса"})
        Address.create_from_api({"ID": 555002, "City": "Одеса"})
        self.assertEqual(Address.search_count([]), before + 2)

    def test_create_does_no_http(self):
        # Пряме створення адреси не має потребувати мережі/креденшала.
        address = self.env["dm.geodata.address"].create({"city": "Суми"})
        self.assertTrue(address.id)
        self.assertEqual(address.city, "Суми")
