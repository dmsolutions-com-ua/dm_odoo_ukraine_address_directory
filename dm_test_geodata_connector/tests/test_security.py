from odoo.tests.common import TransactionCase


class TestSecurity(TransactionCase):
    """A plain internal user (base.group_user, no Geodata group) must be able
    to use autocomplete/apply without AccessError, thanks to the sudo service
    layer (AUDIT #1/#2). Multi-company rules must exist (AUDIT #4)."""

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.env["ir.config_parameter"].sudo().set_param("geodata.test.mock_api", "1")
        cls.env["dm.geodata.api.credential"].create({
            "name": "Sec Mock Cred",
            "api_url": "https://example.test",
            "api_username": "u",
            "api_password": "p",
        })
        cls.user = cls.env["res.users"].create({
            "name": "Plain Internal",
            "login": "geo_plain_user",
            "group_ids": [(6, 0, [cls.env.ref("base.group_user").id])],
        })

    def test_company_rules_exist(self):
        self.assertTrue(self.env.ref("dm_geodata_connector.geodata_address_company_rule"))
        self.assertTrue(
            self.env.ref("dm_geodata_connector.geodata_api_credential_company_rule")
        )

    def test_apply_address_as_plain_user(self):
        api_data = {
            "ID": 700001, "City": "Київ", "CityString": "місто Київ",
            "SettlementType": "місто", "Street": "Хрещатик", "StrType": "вул.",
            "HouseNum": "1", "Index_8x": "01001", "Region": "Київ",
        }
        result = self.env["res.partner"].with_user(self.user).apply_address(
            False, api_data
        )
        self.assertIn("geodata_address_id", result)
        self.assertTrue(result["geodata_address_id"])
        self.assertEqual(result.get("city"), "місто Київ")

    def test_autocomplete_as_plain_user(self):
        res = self.env["res.partner"].with_user(self.user).geodata_autocomplete_cities(
            "Київ", {"country_code": "UA"}
        )
        self.assertTrue(res)
