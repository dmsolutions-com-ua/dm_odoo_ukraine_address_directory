from odoo import release
from odoo.tests.common import TransactionCase


class TestUserAgent(TransactionCase):
    """Усі запити до Geodata.online мають іти з брендованим User-Agent
    (назва модуля + його версія + повна версія Odoo)."""

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.env["ir.config_parameter"].sudo().set_param("geodata.test.mock_api", "1")
        cls.cred = cls.env["dm.geodata.api.credential"].create({
            "name": "Mock Cred",
            "api_url": "https://example.test",
            "api_username": "u",
            "api_password": "p",
        })

    def test_user_agent_format(self):
        ua = self.env["dm.geodata.api.credential"]._user_agent()
        self.assertTrue(ua.startswith("dm_geodata_connector/"))
        self.assertIn("(Odoo %s)" % release.version, ua)
        # Версія модуля присутня в рядку (не порожня).
        module = self.env["ir.module.module"].sudo().search(
            [("name", "=", "dm_geodata_connector")], limit=1
        )
        self.assertTrue(module.installed_version)
        self.assertIn(module.installed_version, ua)

    def test_auth_headers_carry_user_agent(self):
        headers = self.cred._auth_headers()
        self.assertIn("User-Agent", headers)
        self.assertTrue(headers["User-Agent"].startswith("dm_geodata_connector/"))
