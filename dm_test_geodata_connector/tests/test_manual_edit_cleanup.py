from odoo.tests.common import TransactionCase


class TestManualEditCleanup(TransactionCase):
    """A manual edit of the street/house must clear EVERYTHING the level owns.

    Regression: `_geodata_sync_on_manual_change` listed the fields to clear by
    hand — a third copy of "what belongs to the level", next to
    `_CLEAR_BELOW_*` and `_*_RESET`. It had drifted: coordinates were cleared,
    but the metro, the city district and the post index of the PREVIOUS house
    survived. Both branches now build the write from the very same lists that
    drive the suggestion chain, so any future addition to those lists applies
    here automatically.
    """

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.credential = cls.env["dm.geodata.api.credential"].create({
            "name": "Manual Edit Cleanup",
            "api_url": "https://example.test",
            "api_username": "u",
            "api_password": "p",
        })
        cls.ua = cls.env.ref("base.ua")
        cls.Geo = cls.env["dm.geodata.address"]

    def _linked_partner(self):
        """Партнер з адресою до рівня будинку: координати, метро, район, індекс."""
        address = self.Geo.create_from_api({
            "SettlementId": 10, "StreetId": 20, "HouseId": 30,
            "City": "Київ", "SettlementType": "місто", "Region": "Київ",
            "Street": "Хрещатик", "StrType": "вул.", "HouseNum": "1",
            "Index_": "01001", "Lat": "50.4501", "Long": "30.5234",
            "CityDistrict": "Шевченківський",
            "MetroName": "Золоті ворота", "MetroLine": "Сирецько-Печерська",
            "MetroDistance": "150",
        })
        partner = self.env["res.partner"].create({
            "name": "Manual Edit Partner", "country_id": self.ua.id,
        })
        vals = partner._geodata_owner_values(address)
        vals["geodata_address_id"] = address.id
        partner.with_context(geodata_applying=True).write(vals)
        return partner, address

    def _assert_house_level_cleared(self, address):
        for fname in address._HOUSE_RESET:
            self.assertFalse(
                address[fname],
                "%s рівня будинку не очищено при ручній правці" % fname)

    # ------------------------------------------------------------------
    # Дефект зі звіту: «координати зникли, але залишилось метро»
    # ------------------------------------------------------------------
    def test_manual_house_number_clears_whole_house_level(self):
        partner, address = self._linked_partner()
        self.assertEqual(address.metro_station, "Золоті ворота")
        self.assertEqual(address.city_district, "Шевченківський")
        self.assertEqual(address.post_index, "01001")

        # Ручна зміна лише номера будинку (назва вулиці та сама).
        partner.write({"street": "вул. Хрещатик, 99"})

        self.assertFalse(address.house_ref)
        self.assertFalse(address.house_num)
        self.assertFalse(address.metro_station, "метро попереднього будинку лишилось")
        self.assertFalse(address.metro_line)
        self.assertFalse(address.metro_distance)
        self.assertFalse(address.city_district)
        self.assertFalse(address.post_index)
        self.assertFalse(address.latitude)
        self.assertFalse(address.longitude)
        self._assert_house_level_cleared(address)
        # Вулиця лишається підтвердженою — змінився лише номер.
        self.assertTrue(address.street_ref)
        self.assertEqual(address.street, "Хрещатик")

    def test_manual_street_name_clears_street_and_below(self):
        partner, address = self._linked_partner()
        partner.write({"street": "вул. Невідома, 5"})

        self.assertFalse(address.street_ref)
        self.assertFalse(address.street)
        self.assertFalse(address.str_type)
        self.assertFalse(address.street_string)
        for fname in address._CLEAR_BELOW_STREET:
            self.assertFalse(
                address[fname],
                "%s нижче рівня вулиці не очищено при ручній правці" % fname)

    def test_manual_edit_keeps_settlement_level(self):
        # Рівень населеного пункту чинний — його чіпати не можна.
        partner, address = self._linked_partner()
        partner.write({"street": "вул. Невідома, 5"})
        self.assertTrue(address.settlement_ref)
        self.assertEqual(address.city, "Київ")
        self.assertEqual(address.region, "Київ")

    # ------------------------------------------------------------------
    # Хелпер, яким гасять рівні
    # ------------------------------------------------------------------
    def test_blank_values_matches_field_type(self):
        blanks = self.Geo._blank_values(
            ("latitude", "longitude", "metro_station", "post_index"))
        self.assertEqual(blanks["latitude"], 0.0)
        self.assertEqual(blanks["longitude"], 0.0)
        self.assertIs(blanks["metro_station"], False)
        self.assertIs(blanks["post_index"], False)

    def test_blank_values_covers_every_level_list(self):
        # Гард від дрейфу: кожне ім'я в рівневих списках має бути реальним полем.
        for name in (self.Geo._HOUSE_RESET + self.Geo._CLEAR_BELOW_STREET
                     + self.Geo._CLEAR_BELOW_CITY + self.Geo._SETTLEMENT_RESET
                     + self.Geo._STREET_RESET):
            self.assertIn(name, self.Geo._fields,
                          "у рівневому списку є неіснуюче поле %s" % name)
