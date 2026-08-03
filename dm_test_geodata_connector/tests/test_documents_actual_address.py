from odoo.tests.common import TransactionCase


class TestDocumentsActualAddress(TransactionCase):
    """Підхід A: документна/листова адреса будується з ФАКТИЧНОЇ адреси власника
    (стандартні поля Odoo) з відкатом на довідник для порожніх полів.

    Раніше документ рендерився ВИКЛЮЧНО з верифікованого зрізу
    (dm.geodata.address), тож будь-яка введена вручну частина (місто/вулиця/
    будинок), якої ще немає в еталонному довіднику, тихо зникала з договору та
    конверта. Тепер довідник — валідатор і збагачувач, а не фільтр вмісту."""

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.credential = cls.env["dm.geodata.api.credential"].create({
            "name": "A1 Test",
            "api_url": "https://example.test",
            "api_username": "u",
            "api_password": "p",
        })
        cls.ukraine = cls.env.ref("base.ua")

    def _partner_from_directory(self):
        """Партнер з адресою, обраною з довідника до рівня будинку."""
        addr = self.env["dm.geodata.address"].create_from_api({
            "SettlementId": 10, "StreetId": 20, "HouseId": 30,
            "City": "Київ", "SettlementType": "місто", "Region": "Київ",
            "Street": "Хрещатик", "StrType": "вул.",
            "HouseNum": "1", "Index_": "01001",
        })
        partner = self.env["res.partner"].create({
            "name": "A1 Partner",
            "country_id": self.ukraine.id,
        })
        vals = partner._geodata_owner_values(addr)
        vals["geodata_address_id"] = addr.id
        partner.with_context(geodata_applying=True).write(vals)
        return partner, addr

    # ------------------------------------------------------------------
    # Ядро A1: ручні частини не зникають з документа
    # ------------------------------------------------------------------
    def test_manual_house_stays_in_document_and_letter(self):
        partner, addr = self._partner_from_directory()
        self.assertIn("Хрещатик", partner.geodata_address_full_ua or "")

        # Користувач вписує номер будинку, якого немає в довіднику.
        partner.street = "вул. Хрещатик, 15А"
        self.assertFalse(addr.house_ref, "будинок мав стати непідтвердженим")

        doc = partner.geodata_address_full_ua or ""
        letter = partner.geodata_address_letter_ua or ""
        self.assertIn("15А", doc, "ручний номер будинку зник з документної адреси")
        self.assertIn("15А", letter, "ручний номер будинку зник з конвертної адреси")

    def test_manual_city_without_directory_link_still_renders(self):
        # Повністю ручна адреса (немає dm.geodata.address взагалі).
        partner = self.env["res.partner"].create({
            "name": "Ручна адреса",
            "country_id": self.ukraine.id,
            "city": "Новосілка",
            "street": "вул. Польова, 7",
            "zip": "12345",
        })
        self.assertFalse(partner.geodata_address_id)
        doc = partner.geodata_address_full_ua or ""
        self.assertIn("Новосілка", doc, "ручне місто зникло з документної адреси")
        self.assertIn("вул. Польова, 7", doc)
        self.assertIn("12345", doc)

    def test_directory_fallback_when_owner_fields_empty(self):
        # Зв'язок є, owner-поля порожні -> відкат на довідник («АБО довідника»).
        addr = self.env["dm.geodata.address"].create_from_api({
            "SettlementId": 11, "City": "Львів", "SettlementType": "місто",
            "Region": "Львівська обл.", "Index_": "79000",
        })
        partner = self.env["res.partner"].create({
            "name": "Лише зв'язок", "geodata_address_id": addr.id,
        })
        doc = partner.geodata_address_full_ua or ""
        self.assertIn("Львів", doc)
        self.assertIn("79000", doc)

    # ------------------------------------------------------------------
    # По-елементне попередження «не з довідника»
    # ------------------------------------------------------------------
    def test_house_verified_flag_tracks_manual_house(self):
        partner, _addr = self._partner_from_directory()
        self.assertTrue(partner.geodata_house_verified, "будинок обрано з довідника")
        self.assertTrue(partner.geodata_street_verified)

        partner.street = "вул. Хрещатик, 15А"
        self.assertFalse(partner.geodata_house_verified,
                         "будинок введено вручну -> має бути непідтверджений")
        self.assertTrue(partner.geodata_street_verified,
                        "вулиця лишається звіреною (змінився лише номер)")

    # ------------------------------------------------------------------
    # Неймінг плейсхолдерів: gd_ + legacy CamelCase як аліас
    # ------------------------------------------------------------------
    def test_gd_placeholders_and_legacy_aliases(self):
        addr = self.env["dm.geodata.address"].create_from_api({
            "SettlementId": 12, "City": "Львів", "SettlementType": "місто",
            "KATO": "UA46060000000000000",
        })
        self.assertEqual(addr._render_api_template("{gd_city}", "ua"), "Львів")
        self.assertEqual(addr._render_api_template("{gd_kato}", "ua"),
                         "UA46060000000000000")
        # Старі CamelCase-імена лишаються робочими (legacy-аліаси).
        self.assertEqual(addr._render_api_template("{City}", "ua"), "Львів")
        self.assertEqual(addr._render_api_template("{KATO}", "ua"),
                         "UA46060000000000000")

    def test_gd_key_map_covers_legacy_placeholders(self):
        gd_map = self.env["dm.geodata.address"]._GD_KEYS
        for legacy in ("City", "Street", "HouseNum", "HouseNumAdd", "Region",
                       "Area", "Hromada", "Index_", "KATO", "KOATUU", "CityFull",
                       "StreetFull", "HromadaFull", "MetroLine", "MetroLineColor",
                       "TerrStatus", "updated"):
            self.assertIn(legacy, gd_map,
                          "немає gd_-відповідника для {%s}" % legacy)
            self.assertTrue(gd_map[legacy].startswith("gd_"), legacy)

    def test_render_values_works_without_geo_record(self):
        # Рушій має рендерити переданий словник без запису dm.geodata.address.
        Geo = self.env["dm.geodata.address"]
        out = Geo._render_values("{city}, {street}, {zip}", {
            "city": "Ніжин", "street": "вул. Миру, 3", "zip": "16600",
        })
        self.assertEqual(out, "Ніжин, вул. Миру, 3, 16600")
        # Порожні плейсхолдери прибираються разом із роздільником.
        out_empty = Geo._render_values("{city}, {street}, {zip}", {
            "city": "Ніжин", "street": "", "zip": "16600",
        })
        self.assertEqual(out_empty, "Ніжин, 16600")

    # ------------------------------------------------------------------
    # Країна у шаблонах: значення {country} йде з country_id власника, тож
    # документні поля мусять залежати від нього.
    # ------------------------------------------------------------------
    def test_country_change_recomputes_documents(self):
        """`country_id` really is in `@api.depends` of `_compute_geodata_documents`.

        Isolated on a partner WITHOUT a directory link, so the country is the
        only thing that changes: the cascade leaves a manually typed address
        alone, yet `render` turns False once the address is no longer Ukrainian.
        Without the dependency the field would stay cached and keep showing the
        old rendering.
        """
        partner = self.env["res.partner"].create({
            "name": "Ручна адреса, зміна країни",
            "country_id": self.ukraine.id,
            "city": "Ніжин", "street": "вул. Миру, 3",
        })
        before = partner.geodata_address_full_ua or ""
        self.assertIn(self.ukraine.with_context(lang="uk_UA").name, before)
        self.assertIn("Ніжин", before)

        partner.country_id = self.env.ref("base.pl")
        # Ручний ввід не стирається (немає прив'язки), але адреса вже не
        # українська -> документ не рендериться.
        self.assertEqual(partner.city, "Ніжин")
        self.assertFalse(partner.geodata_address_full_ua)

        partner.country_id = self.ukraine
        self.assertEqual(partner.geodata_address_full_ua, before)

    def test_foreign_country_clears_linked_address(self):
        """Країна — повноцінний рівень: іноземна країна знімає прив'язку й
        чистить адресний блок навіть при прямому записі (імпорт/RPC), тож
        документні поля порожніють разом із адресою."""
        partner, _addr = self._partner_from_directory()
        self.assertTrue(partner.geodata_address_full_ua)

        partner.write({"country_id": self.env.ref("base.pl").id})
        self.assertFalse(partner.geodata_address_id)
        self.assertFalse(partner.city)
        self.assertFalse(partner.geodata_address_full_ua)
        self.assertFalse(partner.geodata_address_letter_ua)
