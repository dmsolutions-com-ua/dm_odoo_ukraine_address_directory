from odoo.tests.common import Form, TransactionCase


class TestTranslitLiveSync(TransactionCase):
    """The EN document/envelope address must follow the UA one immediately, not
    one save behind.

    Regression: editing the street on the contact form updated the UA address at
    once, while EN kept the previous street until «Save». `_geodata_doc_values`
    preferred the DIRECTORY value for verified levels, and the directory record
    is only updated by `_geodata_sync_on_manual_change` during `write()` - so
    in-form the EN side was rendering an address the user no longer had.
    """

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.credential = cls.env["dm.geodata.api.credential"].create({
            "name": "Live Sync Test",
            "api_url": "https://example.test",
            "api_username": "u",
            "api_password": "p",
        })
        cls.ua = cls.env.ref("base.ua")

    def _linked_partner(self):
        """Партнер з адресою, обраною з довідника до рівня будинку."""
        address = self.env["dm.geodata.address"].create_from_api({
            "SettlementId": 10, "StreetId": 20, "HouseId": 30,
            "City": "Київ", "SettlementType": "місто", "Region": "Київ",
            "Street": "Хрещатик", "StrType": "вул.",
            "HouseNum": "1", "Index_": "01001",
        })
        partner = self.env["res.partner"].create({
            "name": "Live Sync Partner", "country_id": self.ua.id,
        })
        vals = partner._geodata_owner_values(address)
        vals["geodata_address_id"] = address.id
        partner.with_context(geodata_applying=True).write(vals)
        return partner, address

    # ------------------------------------------------------------------
    # Сценарій зі звіту: правка у формі, ДО збереження
    # ------------------------------------------------------------------
    def test_en_follows_street_edit_before_save(self):
        partner, address = self._linked_partner()
        form = Form(partner)
        self.assertIn("Khreshchatyk", form.geodata_address_full_en,
                      "передумова: EN-документ уже містить вулицю")

        form.street = "вул. Хрещатик, 15А"
        # Довідниковий запис ще НЕ змінився — саме тут раніше й був розрив.
        self.assertTrue(address.street_ref, "передумова: довідник ще не оновлено")

        self.assertIn("15А", form.geodata_address_full_ua)
        self.assertIn("15A", form.geodata_address_full_en,
                      "EN має оновитись одночасно з UA, а не після збереження")
        self.assertIn("15A", form.geodata_address_letter_en,
                      "конверт EN має оновитись так само")

    def test_en_follows_house_number_edit_before_save(self):
        # Зміна лише номера будинку не відв'язує вулицю — той самий розрив.
        partner, _address = self._linked_partner()
        form = Form(partner)
        form.street = "вул. Хрещатик, 7Б"
        self.assertIn("7B", form.geodata_address_full_en)
        self.assertNotIn("Khreshchatyk, 1", form.geodata_address_full_en)

    def test_en_has_no_cyrillic_after_manual_edit(self):
        partner, _address = self._linked_partner()
        form = Form(partner)
        form.street = "вул. Січових Стрільців, 12"
        en_doc = form.geodata_address_full_en or ""
        self.assertIn("Sichovykh Striltsiv", en_doc)
        self.assertFalse([ch for ch in en_doc if "Ѐ" <= ch <= "ӿ"],
                         "у EN-адресу просочилась кирилиця: %s" % en_doc)

    # ------------------------------------------------------------------
    # Значення напряму
    # ------------------------------------------------------------------
    def test_doc_values_transliterate_owner_street(self):
        partner, _address = self._linked_partner()
        # Обходимо write-синхронізацію, щоб відтворити стан «у формі»:
        # owner-поле вже інше, довідник ще старий.
        partner.with_context(geodata_applying=True).write(
            {"street": "вул. Хрещатик, 15А"})
        self.assertEqual(
            partner._geodata_doc_values("en")["street"],
            "vul. Khreshchatyk, 15A")

    def test_empty_owner_field_falls_back_to_directory(self):
        # Відкат на довідник для порожніх owner-полів має лишитись робочим.
        partner, _address = self._linked_partner()
        partner.with_context(geodata_applying=True).write({"street": False})
        self.assertEqual(
            partner._geodata_doc_values("en")["street"],
            "vul. Khreshchatyk, 1")

    # ------------------------------------------------------------------
    # Суфікс громади: обидва шляхи мають давати однаково
    # ------------------------------------------------------------------
    def test_hromada_suffix_matches_translit_table(self):
        Geo = self.env["dm.geodata.address"]
        # За таблицею КМУ №55: г -> h, громада -> hromada.
        self.assertEqual(Geo._hromada_suffix("Sumska", "en"), "Sumska hr.")
        self.assertEqual(Geo._hromada_suffix("Сумська", "ua"), "Сумська гр.")

    def test_hromada_same_in_owner_and_directory_paths(self):
        partner, address = self._linked_partner()
        address.write({"hromada": "Сумська"})
        # Довідниковий шлях (owner-поле порожнє) і owner-шлях мають збігатись.
        from_directory = partner._geodata_doc_values("en")["hromada"]
        partner.with_context(geodata_applying=True).write(
            {"hromada": "Сумська гр."})
        from_owner = partner._geodata_doc_values("en")["hromada"]
        self.assertEqual(from_directory, "Sumska hr.")
        self.assertEqual(from_owner, from_directory)
        self.assertEqual(partner._geodata_doc_values("ua")["hromada"],
                         "Сумська гр.")
