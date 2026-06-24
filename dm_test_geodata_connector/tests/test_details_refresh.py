from odoo.tests.common import TransactionCase


class TestDetailsRefresh(TransactionCase):
    """Regression: the non-stored compute fields of the «Address Information» tab
    (geodata_details_col1/col2, geodata_address_display, document/letter formats)
    must refresh when the LINKED dm.geodata.address is mutated IN PLACE (same id) —
    e.g. picking another city reuses the partner's single address record.

    Root cause was `_compute_geodata_details` depending only on `geodata_address_id`
    (the m2o link). When the link value does not change, mutating the address fields
    did NOT invalidate the partner's cached column, so the tab kept showing the old
    metro/coordinates/territory status of the previously selected city."""

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.credential = cls.env["dm.geodata.api.credential"].create({
            "name": "Refresh Test",
            "api_url": "https://example.test",
            "api_username": "u",
            "api_password": "p",
        })
        # Перше місто: має метро, координати та статус ТОТ (рівень будинку, щоб
        # координати будинку записались).
        cls.address = cls.env["dm.geodata.address"].create_from_api({
            "Id": 1, "City": "Київ", "SettlementType": "місто",
            "Region": "Київ", "Street": "Хрещатик", "StrType": "вул.",
            "HouseNum": "1", "Lat_": 50.45, "Long_": 30.52,
            "MetroStation": "Золоті ворота", "MetroLine": "Лінія 1",
            "MetroDistance": "150", "TerrStatus": "Контрольована",
        })
        cls.partner = cls.env["res.partner"].create({
            "name": "Тест Рефреш",
            "geodata_address_id": cls.address.id,
        })

    def test_details_col2_refreshes_on_inplace_city_switch(self):
        # Перше читання кешує колонку зі старим метро/статусом.
        col2_before = self.partner.geodata_details_col2 or ""
        self.assertIn("Золоті ворота", col2_before)
        self.assertIn("Контрольована", col2_before)

        # Перевибір ІНШОГО міста без метро/координат/статусу на ТОМУ Ж записі
        # (link не змінюється — той самий geodata_address_id). БЕЗ ручної
        # інвалідизації: перевіряємо саме інвалідизацію за залежностями.
        self.address.update_from_api({
            "Id": 2, "City": "Харків", "SettlementType": "місто",
            "Region": "Харківська обл.", "Area": "Харківський р-н",
        })
        self.assertFalse(self.address.metro_station, "дані мали очиститись на рівні запису")

        col2_after = self.partner.geodata_details_col2 or ""
        self.assertNotIn("Золоті ворота", col2_after,
                         "колонка деталей не оновилась — показує старе метро")
        self.assertNotIn("Контрольована", col2_after,
                         "колонка деталей не оновилась — показує старий статус ТОТ")

    def test_tab_compute_fields_depend_on_address_data(self):
        # Детермінований гард фіксу: обидва compute вкладки мають залежати від
        # write_date пов'язаної адреси та адресних полів власника, інакше при
        # мутації адреси «на місці» (незмінений m2o) вони не перерахуються.
        fields = self.env["res.partner"]._fields
        for fname in ("geodata_details_col1", "geodata_details_col2",
                      "geodata_address_display", "geodata_address_full_ua"):
            deps = fields[fname].get_depends(self.env["res.partner"])[0]
            self.assertIn("geodata_address_id.write_date", deps, fname)
            for owner_field in ("city", "street", "zip", "area", "hromada", "state_id"):
                self.assertIn(owner_field, deps, "%s: %s" % (fname, owner_field))

    def test_display_refreshes_on_inplace_city_switch(self):
        # Перший рядок (display) також має оновитись на новий населений пункт.
        _ = self.partner.geodata_address_display  # кешуємо «Київ»
        self.address.update_from_api({
            "Id": 2, "City": "Харків", "SettlementType": "місто",
            "Region": "Харківська обл.",
        })
        display_after = self.partner.geodata_address_display or ""
        self.assertIn("Харків", display_after)
        self.assertNotIn("Хрещатик", display_after,
                         "рядок адреси не оновився — лишилась стара вулиця")

    def test_owner_zip_overrides_directory_index(self):
        # Індекс, введений власником, має пріоритет над довідниковим post_index
        # у документних/конвертних адресах (і в рядку картки).
        self.address.post_index = "01001"
        self.partner.zip = "99999"
        out = self.partner.geodata_address_full_ua or ""
        self.assertIn("99999", out)
        self.assertNotIn("01001", out)
        # Без власного zip — береться довідниковий індекс.
        self.partner.zip = False
        self.assertIn("01001", self.partner.geodata_address_full_ua or "")
