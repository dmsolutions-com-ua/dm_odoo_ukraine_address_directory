from odoo.tests.common import TransactionCase


class TestAddressOwnership(TransactionCase):
    """Strict 1:1 ownership: each owner has its OWN private dm.geodata.address (no
    dedup, no sharing); detaching or deleting the owner removes the orphan row."""

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.ua = cls.env.ref("base.ua", raise_if_not_found=False)
        cls.Geo = cls.env["dm.geodata.address"]
        cls.P = cls.env["res.partner"]

    def _linked_partner(self, name):
        addr = self.Geo.create_from_api(
            {"Id": 1, "City": "Київ", "SettlementType": "місто"})
        partner = self.P.create({
            "name": name,
            "country_id": self.ua.id if self.ua else False,
            "geodata_address_id": addr.id,
        })
        return partner, addr

    def test_two_owners_get_distinct_rows(self):
        p1, a1 = self._linked_partner("Owner 1")
        p2, a2 = self._linked_partner("Owner 2")
        self.assertNotEqual(a1.id, a2.id, "Identical addresses must not be shared")
        self.assertNotEqual(p1.geodata_address_id, p2.geodata_address_id)

    def test_reset_deletes_orphan(self):
        partner, addr = self._linked_partner("Owner R")
        partner.action_geodata_reset()
        self.assertFalse(partner.geodata_address_id)
        self.assertFalse(addr.exists(), "Private row deleted on reset")

    def test_mixin_field_map_and_owner_fields(self):
        # Перевикористовуваний міксин надає area/hromada і типову мапу полів-
        # ідентичностей; _geodata_owner_values повертає (реальні) імена полів власника.
        self.assertEqual(self.P._geodata_fields["city"], "city")
        self.assertIn("area", self.P._fields)
        self.assertIn("hromada", self.P._fields)
        addr = self.Geo.create_from_api(
            {"Id": 1, "City": "Київ", "SettlementType": "місто"})
        owner_vals = self.P._geodata_owner_values(addr)
        self.assertIn("city", owner_vals)
        self.assertEqual(owner_vals["city"], "місто Київ")

    def test_owner_unlink_deletes_address(self):
        partner, addr = self._linked_partner("Owner D")
        partner.unlink()
        self.assertFalse(addr.exists(), "Private row deleted with its owner")
