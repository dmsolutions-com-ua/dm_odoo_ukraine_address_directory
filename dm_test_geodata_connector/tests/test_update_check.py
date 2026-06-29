from unittest.mock import patch

from odoo.tests.common import TransactionCase

_MODEL = "dm.geodata.api.credential"
_HIGH = "99.0.0.0"  # завідомо новіша за встановлену версію ядра


class TestUpdateCheck(TransactionCase):
    """Перевірка оновлень: банер + нотифікація менеджерам, вимикач, дедуп."""

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.params = cls.env["ir.config_parameter"].sudo()
        cls.cred = cls.env[_MODEL].create({
            "name": "Mock Cred",
            "api_url": "https://example.test",
            "api_username": "u",
            "api_password": "p",
        })

    def _patch_fetch(self, version):
        return patch.object(
            type(self.env[_MODEL]), "_fetch_latest_published_version",
            return_value=version,
        )

    def test_update_available_and_notifies(self):
        with self._patch_fetch(_HIGH), \
                patch.object(type(self.env[_MODEL]), "_geodata_push") as push:
            self.env[_MODEL]._check_connector_update()
            push.assert_called_once()
        self.assertEqual(self.params.get_param("geodata.update_latest_version"), _HIGH)
        self.cred.invalidate_recordset()
        self.assertTrue(self.cred.update_available)
        self.assertEqual(self.cred.latest_version, _HIGH)

    def test_dismiss_hides_banner(self):
        self.params.set_param("geodata.update_latest_version", _HIGH)
        self.cred.invalidate_recordset()
        self.assertTrue(self.cred.update_available)
        self.cred.action_dismiss_update()
        self.cred.invalidate_recordset()
        self.assertFalse(self.cred.update_available)

    def test_disabled_skips(self):
        self.params.set_param("geodata.update_check_enabled", "0")
        with self._patch_fetch(_HIGH), \
                patch.object(type(self.env[_MODEL]), "_geodata_push") as push:
            result = self.env[_MODEL]._check_connector_update()
            push.assert_not_called()
        self.assertFalse(result)

    def test_no_renotify_same_version(self):
        self.params.set_param("geodata.update_notified_version", _HIGH)
        with self._patch_fetch(_HIGH), \
                patch.object(type(self.env[_MODEL]), "_geodata_push") as push:
            self.env[_MODEL]._check_connector_update()
            push.assert_not_called()
