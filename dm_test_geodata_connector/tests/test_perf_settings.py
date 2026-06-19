from datetime import timedelta
from unittest.mock import patch

from odoo import fields
from odoo.exceptions import ValidationError
from odoo.tests.common import TransactionCase


class TestMonikerReuse(TransactionCase):
    """Street suggestions must REUSE the stored, still-fresh city moniker (~15 min)
    instead of re-resolving it via API Cities every time (revenue goal: no wasted
    technical duplicate calls; real searches still bill)."""

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.env["ir.config_parameter"].sudo().set_param("geodata.test.mock_api", "1")
        cls.env["dm.geodata.api.credential"].create({
            "name": "Moniker Mock", "api_url": "https://example.test",
            "api_username": "u", "api_password": "p",
        })
        cls.P = cls.env["res.partner"]
        cls.ua = cls.env.ref("base.ua", raise_if_not_found=False)

    def _linked(self, **addr_vals):
        addr = self.env["dm.geodata.address"].create(dict({
            "settlement_ref": 1, "city": "Київ", "settlement_type": "місто",
            "kato": "UA80000000000093317",
            "city_moniker": "m-stored", "city_moniker_ts": fields.Datetime.now(),
        }, **addr_vals))
        p = self.P.create({"name": "M", "country_id": self.ua.id if self.ua else False})
        p.with_context(geodata_applying=True).write({"geodata_address_id": addr.id})
        return p, addr

    def test_fresh_stored_moniker_skips_api_cities(self):
        p, addr = self._linked()
        dep = {"country_code": "UA", "geodata_address_id": addr.id}
        with patch.object(type(p), "_refresh_city_moniker", return_value="x") as spy:
            res = p.geodata_autocomplete_streets("Хрещатик", dep)
        spy.assert_not_called()  # свіжий монікер -> без повторного API Cities
        self.assertTrue(res)

    def test_stale_stored_moniker_reresolves(self):
        p, addr = self._linked(
            city_moniker_ts=fields.Datetime.now() - timedelta(minutes=20))
        dep = {"country_code": "UA", "geodata_address_id": addr.id}
        with patch.object(type(p), "_refresh_city_moniker", return_value="m-new") as spy:
            p.geodata_autocomplete_streets("Хрещатик", dep)
        spy.assert_called()  # >15 хв -> монікер недійсний -> ре-резолв (API Cities)

    def test_ingestion_sets_moniker_timestamp(self):
        addr = self.env["dm.geodata.address"].create_from_api(
            {"Id": 1, "City": "Київ", "st_moniker": "m"})
        self.assertEqual(addr.city_moniker, "m")
        self.assertTrue(addr.city_moniker_ts, "moniker timestamp must be set on ingest")


class TestMinCharsConstraint(TransactionCase):

    def test_min_chars_below_3_rejected(self):
        with self.assertRaises(ValidationError):
            self.env["dm.geodata.api.credential"].create({
                "name": "Bad MinChars", "api_url": "https://example.test",
                "api_username": "u", "api_password": "p", "min_chars": 2,
            })
