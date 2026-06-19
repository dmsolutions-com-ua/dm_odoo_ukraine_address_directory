from odoo.tests.common import Form, TransactionCase


class TestAddressSync(TransactionCase):
    """v1.5: verified-only model, clear-down, manual downgrade/detach,
    verified flags and transparent moniker re-resolve."""

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.env["ir.config_parameter"].sudo().set_param("geodata.test.mock_api", "1")
        cls.env["dm.geodata.api.credential"].create({
            "name": "Sync Mock Cred",
            "api_url": "https://example.test",
            "api_username": "u",
            "api_password": "p",
        })
        cls.P = cls.env["res.partner"]
        cls.Geo = cls.env["dm.geodata.address"]
        cls.ua = cls.env.ref("base.ua", raise_if_not_found=False)

    def _addr(self, **vals):
        return self.Geo.create(vals)

    def _partner(self, addr, **vals):
        p = self.P.create(dict({"name": "Sync P",
                                "country_id": self.ua.id if self.ua else False}, **vals))
        p.with_context(geodata_applying=True).write({"geodata_address_id": addr.id})
        return p

    # --- Частина 1: clear-down при повторному виборі вищого рівня (#4) ---
    def test_clear_down_city_drops_street(self):
        a = self.Geo.create_from_api({"Id": 1, "City": "Київ", "SettlementType": "місто",
                                      "st_moniker": "m"})
        a.update_from_api({"StreetId": 50, "Street": "Хрещатик", "StreetType": "вул.",
                           "house_moniker": "hm"})
        self.assertEqual(a.street, "Хрещатик")
        # Повторний вибір міста -> вулиця/будинок мають очиститись.
        a.update_from_api({"Id": 1, "City": "Київ", "SettlementType": "місто"})
        self.assertFalse(a.street)
        self.assertFalse(a.street_ref)

    # --- Частина 3: прапорці підтвердження ---
    def test_verified_flags(self):
        a = self._addr(settlement_ref=1, city="Київ", settlement_type="місто")
        p = self._partner(a)
        self.assertTrue(p.geodata_city_verified)
        self.assertFalse(p.geodata_street_verified)
        self.assertEqual(p.geodata_verified_level, "settlement")
        a.write({"street_ref": 50, "street": "Хрещатик"})
        p.invalidate_recordset()
        self.assertTrue(p.geodata_street_verified)
        self.assertEqual(p.geodata_verified_level, "street")

    # --- Частина 2: ручна зміна вулиці (інша вулиця) -> пониження, зв'язок лишається ---
    def test_manual_street_downgrade(self):
        a = self._addr(settlement_ref=1, street_ref=50, house_ref=9,
                       city="Київ", settlement_type="місто",
                       str_type="вул.", street="Хрещатик", house_num="1")
        p = self._partner(a, city="місто Київ", street="вул. Хрещатик 1", zip="01001")
        p.write({"street": "вул. Інша, 5"})
        a.invalidate_recordset()
        self.assertEqual(p.geodata_address_id, a, "Link kept (settlement still valid)")
        self.assertFalse(a.street_ref, "Street downgraded")
        self.assertFalse(p.geodata_street_verified)
        self.assertTrue(p.geodata_city_verified)

    # --- Жива перевірка вулиці: ручна зміна назви знімає підтвердження одразу ---
    def test_street_manual_change_unverifies_live(self):
        a = self._addr(settlement_ref=1, street_ref=50, city="Київ",
                       settlement_type="місто", str_type="вул.", street="Хрещатик")
        p = self._partner(a, city="місто Київ", street="вул. Хрещатик")
        p.invalidate_recordset()
        self.assertTrue(p.geodata_street_verified)
        # Ручна зміна НАЗВИ вулиці у формі (onchange) -> не підтверджено БЕЗ save.
        form = Form(p)
        form.street = "вул. Інша"
        self.assertFalse(
            form.geodata_street_verified,
            "Manual street rename must unverify live (onchange, before save)")
        # Зміна лише номера будинку -> вулиця лишається підтвердженою.
        form2 = Form(p)
        form2.street = "вул. Хрещатик, 7"
        self.assertTrue(
            form2.geodata_street_verified,
            "House-only change keeps the street verified")

    # --- Частина 2: правка лише будинку лишає вулицю підтвердженою (#2) ---
    def test_house_only_keeps_street(self):
        a = self._addr(settlement_ref=1, street_ref=50, house_ref=9,
                       city="Київ", settlement_type="місто",
                       str_type="вул.", street="Хрещатик", house_num="1")
        p = self._partner(a, city="місто Київ", street="вул. Хрещатик 1")
        p.write({"street": "вул. Хрещатик, 1Б"})
        a.invalidate_recordset()
        self.assertEqual(a.street_ref, 50, "Street stays validated")
        self.assertFalse(a.house_ref, "House downgraded")

    # --- Частина 2: ручна зміна міста -> відв'язування + очищення похідних area/hromada (#1) ---
    def test_manual_city_detaches(self):
        a = self._addr(settlement_ref=1, city="Київ", settlement_type="місто",
                       area="Києво-Святошинський р-н", hromada="Київська")
        p = self._partner(a, city="місто Київ",
                          area="Києво-Святошинський р-н", hromada="Київська")
        p.write({"city": "Інше місто"})
        self.assertFalse(p.geodata_address_id, "Link detached on settlement change")
        self.assertFalse(p.area, "District cleared (derived from settlement)")
        self.assertFalse(p.hromada, "Hromada cleared (derived from settlement)")

    # --- Частина 4: прозоре переотримання moniker міста (без кнопок) ---
    def test_moniker_reresolve(self):
        a = self._addr(settlement_ref=1, city="Київ", settlement_type="місто",
                       kato="UA80000000000093317")  # city_moniker empty -> must re-resolve
        dep = {"country_code": "UA", "geodata_address_id": a.id}
        res = self.P.geodata_autocomplete_streets("Хрещатик", dep)
        self.assertTrue(res, "Streets returned after transparent moniker re-resolve")
        self.assertEqual(res[0]["label"], "вул. Хрещатик")
        a.invalidate_recordset()
        self.assertTrue(a.city_moniker, "Fresh city moniker persisted")
