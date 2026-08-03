from odoo.tests.common import Form, TransactionCase


class TestDetailsLiveSync(TransactionCase):
    """The «Address details» columns must stop showing house/street data of the
    directory as soon as the owner edits away from it - not one save later.

    Regression: `_compute_geodata_details` renders straight from the linked
    dm.geodata.address, and that row is downgraded only by
    `_geodata_sync_on_manual_change` during `write()`. So after changing the
    street/house in the form, column 2 kept the OLD building's coordinates and
    its «Google Maps» button pointed at a different address until «Save».

    Only the diverged level is blanked: КАТОТТГ/КОАТУУ and the territory status
    are settlement-level and stay valid.
    """

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.credential = cls.env["dm.geodata.api.credential"].create({
            "name": "Details Live Sync",
            "api_url": "https://example.test",
            "api_username": "u",
            "api_password": "p",
        })
        cls.ua = cls.env.ref("base.ua")

    def _linked_partner(self):
        """Партнер з адресою до рівня будинку: є координати, метро й коди."""
        address = self.env["dm.geodata.address"].create_from_api({
            "SettlementId": 10, "StreetId": 20, "HouseId": 30,
            "City": "Київ", "SettlementType": "місто", "Region": "Київ",
            "Street": "Хрещатик", "StrType": "вул.", "HouseNum": "1",
            "Index_": "01001", "Lat_": 50.45, "Long_": 30.52,
            "MetroStation": "Золоті ворота", "MetroLine": "Сирецько-Печерська",
            "MetroDistance": "150", "TerrStatus": "Контрольована",
            "KATO": "UA80000000000093317", "KOATUU": "8000000000",
        })
        partner = self.env["res.partner"].create({
            "name": "Details Live Sync Partner", "country_id": self.ua.id,
        })
        vals = partner._geodata_owner_values(address)
        vals["geodata_address_id"] = address.id
        partner.with_context(geodata_applying=True).write(vals)
        return partner, address

    # ------------------------------------------------------------------
    # Сценарій зі звіту: правка у формі, ДО збереження
    # ------------------------------------------------------------------
    def test_col2_drops_house_data_on_street_edit_before_save(self):
        partner, address = self._linked_partner()
        form = Form(partner)
        col2_before = form.geodata_details_col2 or ""
        self.assertIn("50.45", col2_before, "передумова: координати показані")
        self.assertIn("Золоті ворота", col2_before)

        form.street = "вул. Невідома, 999"
        self.assertTrue(address.house_ref, "передумова: довідник ще не понижено")

        col2 = form.geodata_details_col2 or ""
        self.assertNotIn("50.45", col2,
                         "координати старого будинку лишились у колонці 2")
        self.assertNotIn("30.52", col2)
        self.assertNotIn("Золоті ворота", col2, "метро старої адреси лишилось")
        # Рівень населеного пункту чинний — колонка 1 має вціліти.
        self.assertIn("UA80000000000093317", form.geodata_details_col1 or "")

    def test_col2_drops_house_data_on_house_number_edit(self):
        # Зміна лише номера будинку не відв'язує вулицю, але координати вже інші.
        partner, _address = self._linked_partner()
        form = Form(partner)
        form.street = "вул. Хрещатик, 77"
        col2 = form.geodata_details_col2 or ""
        self.assertNotIn("50.45", col2)
        self.assertNotIn("Золоті ворота", col2)
        self.assertIn("UA80000000000093317", form.geodata_details_col1 or "")

    def test_house_verification_is_live(self):
        partner, _address = self._linked_partner()
        form = Form(partner)
        self.assertTrue(form.geodata_house_verified, "передумова: будинок з довідника")

        form.street = "вул. Хрещатик, 77"
        self.assertFalse(form.geodata_house_verified,
                         "помітка «введено вручну» на будинку має з'явитись одразу")
        self.assertTrue(form.geodata_street_verified,
                        "назва вулиці не змінилась — вона лишається підтвердженою")

    def test_no_edit_keeps_everything(self):
        partner, _address = self._linked_partner()
        form = Form(partner)
        col2 = form.geodata_details_col2 or ""
        self.assertIn("50.45", col2)
        self.assertIn("Золоті ворота", col2)
        self.assertIn("UA80000000000093317", form.geodata_details_col1 or "")

    # ------------------------------------------------------------------
    # Рівні напряму
    # ------------------------------------------------------------------
    def test_diverged_levels(self):
        partner, _address = self._linked_partner()
        self.assertEqual(partner._geodata_diverged_levels(),
                         {"street": False, "house": False})

        partner.with_context(geodata_applying=True).write(
            {"street": "вул. Хрещатик, 77"})
        self.assertEqual(partner._geodata_diverged_levels(),
                         {"street": False, "house": True})

        partner.with_context(geodata_applying=True).write(
            {"street": "вул. Невідома, 999"})
        self.assertEqual(partner._geodata_diverged_levels(),
                         {"street": True, "house": True})

    def test_no_owner_street_diverges_from_nothing(self):
        # Поки підказка застосовується, значення ще не в полі власника —
        # це не привід гасити довідникові дані.
        partner, _address = self._linked_partner()
        partner.with_context(geodata_applying=True).write({"street": False})
        self.assertEqual(partner._geodata_diverged_levels(),
                         {"street": False, "house": False})
        self.assertIn("50.45", partner.geodata_details_col2 or "")

    def test_owner_zip_survives_blanking(self):
        # {Index_} — власний zip власника, він має пережити гасіння
        # довідникового {gd_index}.
        partner, _address = self._linked_partner()
        partner.with_context(geodata_applying=True).write(
            {"zip": "99999", "street": "вул. Невідома, 999"})
        # Той самий порядок, що й у _compute_geodata_details.
        extra = partner._geodata_stale_values(partner._geodata_diverged_levels())
        extra.update(partner._geodata_owner_extra())
        values = partner.geodata_address_id._api_template_values("ua", extra)
        self.assertEqual(values["Index_"], "99999")
        self.assertEqual(values["gd_index"], "")
