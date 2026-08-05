from unittest.mock import patch

from odoo.tests.common import TransactionCase


class TestAddressFormat(TransactionCase):
    """Шаблони адрес на сирих даних API: імена плейсхолдерів = імена полів API,
    значення сирі 1:1 (без авто-склейок), порожні поля стискаються."""

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.credential = cls.env["dm.geodata.api.credential"].create({
            "name": "Format Test",
            "api_url": "https://example.test",
            "api_username": "u",
            "api_password": "p",
        })
        cls.address = cls.env["dm.geodata.address"].create({
            "region": "Київ",
            "city": "Київ",
            "settlement_type": "місто",
            "str_type": "вул.",
            "street": "Хрещатик",
            "house_num": "1",
            "post_index": "01001",
        })
        # {country} береться з res.country, а назва там перекладна — тож
        # очікування будуємо з того самого джерела, а не з літерала (інакше тест
        # червонітиме на БД без встановленої української локалі).
        ukraine = cls.env.ref("base.ua")
        cls.ua_name = cls._expected_country_name(ukraine, "uk_UA")
        cls.en_name = ukraine.with_context(lang="en_US").name

    @classmethod
    def _expected_country_name(cls, country, lang_code):
        """Очікувана назва країни для мови адреси.

        Підміняти `lang` можна лише активною мовою — Odoo 18 інакше кидає
        «Invalid language code». На базі без української модуль віддає власний
        відкат для України (див. `dm.geodata.address._country_name`).
        """
        installed = {c for c, _name in cls.env["res.lang"].get_installed()}
        if lang_code in installed:
            return country.with_context(lang=lang_code).name
        return "Україна" if country.code == "UA" else country.name

    # --- Дефолтний документний шаблон (сирий) ---------------------------------
    def test_default_document_raw_ua(self):
        self.address._compute_full_addresses()
        self.assertEqual(
            self.address.address_full_ua,
            "%s, 01001, місто Київ, вул. Хрещатик, 1" % self.ua_name,
        )

    def test_default_letter_ua(self):
        # Конверт не має {country}, тож без чистих імен рядок був би повністю
        # порожній (усі плейсхолдери рядка порожні -> рушій викидає рядок).
        self.address._compute_full_addresses()
        self.assertEqual(
            self.address.address_letter_ua,
            "вул. Хрещатик, 1, місто Київ, 01001",
        )

    def test_default_document_en(self):
        # Дефолтний шаблон на боці довідника + локальна транслітерація.
        self.address._compute_full_addresses()
        self.assertEqual(
            self.address.address_full_en,
            "%s, 01001, misto Kyiv, vul. Khreshchatyk, 1" % self.en_name,
        )

    # --- {country} з довідника res.country, а не літерал -----------------------
    def test_country_comes_from_res_country_per_address_lang(self):
        # Назва перекладна, тож мова АДРЕСИ (ua/en), а не мова користувача.
        self.assertEqual(
            self.address._render_api_template("{country}", "ua"), self.ua_name)
        self.assertEqual(
            self.address._render_api_template("{country}", "en"), self.en_name)
        # На моделі довідника власника немає -> завжди Україна.
        self.assertEqual(
            self.env["dm.geodata.address"]._country_name("ua"), self.ua_name)

    def test_country_follows_owner_country_id(self):
        # У власника країна вирішує: {country} — не захардкоджена Україна.
        poland = self.env.ref("base.pl")
        partner = self.env["res.partner"].create({
            "name": "PL Partner", "country_id": poland.id,
            "city": "Warszawa", "street": "Marszalkowska 1",
        })
        vals = partner._geodata_doc_values("ua")
        self.assertEqual(vals["country"], self._expected_country_name(poland, "uk_UA"))
        self.assertNotEqual(vals["country"], self.ua_name)

    def test_country_survives_inactive_address_language(self):
        """Мова адреси, не активована в базі, не мусить ламати рендер.

        Odoo 18 кидає UserError «Invalid language code: uk_UA» на
        `with_context(lang=…)` з неактивною мовою — на англомовній базі це
        валило застосування підказки (to_address_values -> {country}).
        """
        Geo = self.env["dm.geodata.address"]
        with patch.dict(Geo._LANG_CODES, {"ua": "zz_ZZ"}):
            self.assertIsNone(Geo._active_lang_code("ua"))
            # Україна лишається українською навіть без встановленої локалі.
            self.assertEqual(Geo._country_name("ua"), "Україна")
            self.assertEqual(
                self.address._render_api_template("{country}", "ua"), "Україна")
            self.assertTrue(self.address.to_address_values()["city"])

    def test_country_falls_back_to_ukraine_when_owner_has_none(self):
        partner = self.env["res.partner"].create({
            "name": "No country", "country_id": False, "city": "Київ",
        })
        self.assertEqual(partner._geodata_doc_values("ua")["country"], self.ua_name)

    # --- Чисті (owner-)імена на боці довідника --------------------------------
    def test_clean_names_equal_directory_values(self):
        # На dm.geodata.address власника немає, тож {city}/{street}/{zip}/{state}
        # дорівнюють довідниковим значенням ({gd_city_full}/{gd_street_full}+буд./
        # {gd_index}/нормалізований {gd_region}).
        addr = self.env["dm.geodata.address"].create({
            "region": "Львівська обл.", "area": "Личаківський р-н",
            "city": "Львів", "settlement_type": "місто",
            "str_type": "вул.", "street": "Личаківська",
            "house_num": "5", "house_num_add": "Б", "post_index": "79000",
        })
        self.assertEqual(addr._render_api_template("{city}", "ua"), "місто Львів")
        self.assertEqual(
            addr._render_api_template("{street}", "ua"), "вул. Личаківська, 5Б")
        self.assertEqual(addr._render_api_template("{zip}", "ua"), "79000")
        # {state} — без суфікса «обл.», як назва res.country.state.
        self.assertEqual(addr._render_api_template("{state}", "ua"), "Львівська")
        self.assertEqual(
            addr._render_api_template("{area}", "ua"), "Личаківський р-н")
        # street2 (кв./офіс) існує лише у власника.
        self.assertEqual(addr._render_api_template("{street2}", "ua"), "")

    def test_clean_and_gd_names_stay_distinct(self):
        # Чисте ім'я і `gd_` дають однакове значення лише тому, що власника тут
        # немає; сирий CamelCase лишається сирим (без склейки типу з назвою).
        self.assertEqual(
            self.address._render_api_template("{city}", "ua"), "місто Київ")
        self.assertEqual(
            self.address._render_api_template("{gd_city_full}", "ua"), "місто Київ")
        self.assertEqual(
            self.address._render_api_template("{City}", "ua"), "Київ")

    # --- Сирі значення без склейок --------------------------------------------
    def test_raw_values_no_merge(self):
        # {City} != "місто Київ": settlement_type окремо; {Hromada} без «гр.»;
        # {Street} без типу; {HouseNum} без коми.
        self.address.hromada = "Київська"
        self.assertEqual(self.address._render_api_template("{City}", "ua"), "Київ")
        self.assertEqual(
            self.address._render_api_template("{SettlementType}", "ua"), "місто")
        self.assertEqual(
            self.address._render_api_template("{Hromada}", "ua"), "Київська")
        self.assertEqual(
            self.address._render_api_template("{Street}", "ua"), "Хрещатик")
        self.assertEqual(
            self.address._render_api_template("{StrType} {Street}", "ua"),
            "вул. Хрещатик")

    # --- Стискання роздільників навколо порожніх полів ------------------------
    def test_separator_squeeze_middle(self):
        # {Area} порожнє посередині -> без «, ,». ({Region} для Києва не беремо —
        # він придушується як дубль міста спецстатусу; тут потрібне непорожнє
        # сусіднє поле.)
        self.assertEqual(
            self.address._render_api_template("{City}, {Area}, {Index_}", "ua"),
            "Київ, 01001")

    def test_separator_squeeze_edges(self):
        # Порожні поля на краях -> провідні/завершальні роздільники прибираються.
        self.assertEqual(
            self.address._render_api_template("{Area}, {City}, {Apartment}", "ua"),
            "Київ")

    # --- Багаторядковий шаблон: порожні рядки ховаються -----------------------
    def test_multiline_hides_empty_lines(self):
        self.address.kato = "UA80000000000093317"
        result = self.address._render_api_template(
            "Коди\nКАТОТТГ: {KATO}\nКв: {Apartment}", "ua")
        self.assertEqual(result, "Коди\nКАТОТТГ: UA80000000000093317")

    def test_free_text_preserved(self):
        self.address.terr_status = "Деокупована"
        self.assertEqual(
            self.address._render_api_template("Статус ТОТ: {TerrStatus}.", "ua"),
            "Статус ТОТ: Деокупована.")

    # --- Odoo-поля власника (extra) -------------------------------------------
    def test_owner_extra_placeholders(self):
        extra = {"partner_name": "ТОВ Ромашка", "company_name": "Ромашка",
                 "street2": "оф. 5"}
        self.assertEqual(
            self.address._render_api_template(
                "{partner_name} | {company_name} | {street2}", "ua", extra),
            "ТОВ Ромашка | Ромашка | оф. 5")

    def test_curated_contact_fields(self):
        partner = self.env["res.partner"].create({
            "name": "Іван Петренко", "vat": "1234567890",
            "phone": "+380441112233", "function": "Директор",
        })
        extra = partner._geodata_owner_extra()
        # Усі куровані ключі присутні.
        for key in ("name", "partner_name", "company_name", "vat", "ref",
                    "function", "title", "phone", "mobile", "email", "street2"):
            self.assertIn(key, extra)
        self.assertEqual(extra["name"], "Іван Петренко")
        self.assertEqual(extra["vat"], "1234567890")
        self.assertEqual(extra["function"], "Директор")
        self.assertEqual(extra["mobile"], "")  # не задано -> порожньо
        # Рендер шаблону з контактними полями; порожні без «дірок».
        self.assertEqual(
            self.address._render_api_template(
                "{name}, {vat}, тел. {phone}, {mobile}", "ua", extra),
            "Іван Петренко, 1234567890, тел. +380441112233")

    # --- Заповнення адресного блоку шаблонами ---------------------------------
    def test_block_templates_to_address_values(self):
        self.address.write({"area": "Сумський р-н", "hromada": "Сумська"})
        vals = self.address.to_address_values()
        self.assertEqual(vals["city"], "місто Київ")          # {CityFull}
        self.assertEqual(vals["street"], "вул. Хрещатик, 1")  # {StreetFull},{HouseNum}
        self.assertFalse(vals["street2"])                     # порожній шаблон
        self.assertEqual(vals["area"], "Сумський р-н")        # {Area} ({AreaOld})
        self.assertEqual(vals["hromada"], "Сумська гр.")      # {HromadaFull}

    def test_hromada_full_empty_no_artifact(self):
        # Без громади {HromadaFull} -> «» (без артефакту «гр.»).
        self.assertFalse(self.address.to_address_values()["hromada"])

    # --- Розумні старі назви {CityFull} --------------------------------------
    def test_city_full_rename(self):
        addr = self.env["dm.geodata.address"].create({
            "settlement_type": "село", "city": "Іванівка",
            "settlement_type_old": "селище", "city_old": "Калинівка"})
        self.assertEqual(
            addr._render_api_template("{CityFull}", "ua"),
            "село Іванівка (селище Калинівка)")

    def test_city_full_type_only(self):
        addr = self.env["dm.geodata.address"].create({
            "settlement_type": "село", "city": "Іванівка",
            "settlement_type_old": "селище"})  # назва не змінювалась
        self.assertEqual(
            addr._render_api_template("{CityFull}", "ua"),
            "село (селище) Іванівка")

    # --- EN: значення з _en (локальна транслітерація UA) -----------------------
    def test_en_uses_en_columns(self):
        addr = self.env["dm.geodata.address"].create({
            "city": "Львів",
            "str_type": "вул.",
            "street": "Личаківська",
        })
        self.assertEqual(addr._render_api_template("{City}", "en"), "Lviv")
        self.assertEqual(
            addr._render_api_template("{StrType} {Street}", "en"), "vul. Lychakivska")
        self.assertEqual(addr._render_api_template("{City}", "ua"), "Львів")

    def test_en_translits_fields_without_en_column(self):
        # Поля без `_en`-двійника (напр. Suburb) транслітеруються на льоту,
        # щоб кирилиця не просочилася в англомовну адресу.
        addr = self.env["dm.geodata.address"].create({
            "city": "Львів", "suburb": "Левандівка",
        })
        self.assertEqual(addr._render_api_template("{Suburb}", "en"), "Levandivka")
        self.assertEqual(addr._render_api_template("{Suburb}", "ua"), "Левандівка")

    def test_en_keeps_non_text_values_intact(self):
        # Координати/прапорці не є текстом — транслітерація їх не чіпає.
        addr = self.env["dm.geodata.address"].create({
            "city": "Львів", "latitude": 49.8397, "is_regional_center": True,
        })
        self.assertEqual(addr._render_api_template("{Lat_}", "en"), "49.8397")

    # --- Кастомний документний шаблон -----------------------------------------
    def test_custom_document_format(self):
        self.credential.address_format_document = "{City}, {Street}, {HouseNum}"
        self.address.invalidate_recordset(["address_full_ua"])
        self.address._compute_full_addresses()
        self.assertEqual(self.address.address_full_ua, "Київ, Хрещатик, 1")

    def test_unknown_placeholder_is_empty(self):
        # Невідомий плейсхолдер -> порожньо (валідації немає, гнучко).
        self.assertEqual(
            self.address._render_api_template("{City} {Bogus}", "ua"), "Київ")

    # --- Правило порожніх обгорток --------------------------------------------
    def test_empty_wrapper_removed(self):
        # city_old порожнє -> "({CityOld})" зникає разом з дужками.
        self.assertEqual(
            self.address._render_api_template("{City} ({CityOld})", "ua"), "Київ")

    def test_filled_wrapper_kept(self):
        self.address.city_old = "Старе"
        self.assertEqual(
            self.address._render_api_template("{City} ({CityOld})", "ua"),
            "Київ (Старе)")

    def test_standalone_empty_wrapper(self):
        # Рядок лише з порожнім обгорнутим плейсхолдером -> ховається.
        self.assertEqual(
            self.address._render_api_template("({CityOld})", "ua"), "")

    # --- Узагальнене правило дужок (фрагмент із текстом) ----------------------
    def test_group_with_text_removed_when_empty(self):
        # Порожній плейсхолдер усередині дужок -> увесь фрагмент зникає.
        self.assertEqual(
            self.address._render_api_template("{City} (стара {CityOld})", "ua"),
            "Київ")

    def test_group_with_text_kept(self):
        self.address.city_old = "Червоне"
        self.assertEqual(
            self.address._render_api_template("{City} (стара {CityOld})", "ua"),
            "Київ (стара Червоне)")

    def test_literal_parens_kept(self):
        # Дужки без плейсхолдерів лишаються як є.
        self.assertEqual(
            self.address._render_api_template("{City} (головний)", "ua"),
            "Київ (головний)")

    def test_terr_status_with_date_group(self):
        self.address.terr_status = "Деокупована"
        r = self.address._render_api_template(
            "{TerrStatus} (на дату {updated})", "ua")
        self.assertTrue(r.startswith("Деокупована (на дату "))
        self.assertTrue(r.endswith(")"))

    # --- HTML-колонки: адмінська розмітка + лінки -----------------------------
    def test_html_finalize_keeps_markup_and_links(self):
        finalize = self.env["res.partner"]._geodata_html_finalize
        out = str(finalize(
            "<b>МЕТРО</b>\nКарта: https://m/?q=1,2\n"
            "<table>\n<tr><td>A</td></tr>\n</table>"))
        # Адмінська розмітка зберігається (не екранується).
        self.assertIn("<b>МЕТРО</b>", out)
        self.assertIn("<table><tr><td>A</td></tr></table>", out)
        self.assertNotIn("&lt;", out)
        # Бари URL клікабельні.
        self.assertIn('<a href="https://m/?q=1,2" target="_blank"', out)
        # Перенос поза тегами -> <br/>.
        self.assertIn("<b>МЕТРО</b><br/>", out)

    def test_escape_values_escapes_api_data(self):
        addr = self.env["dm.geodata.address"].create({"city": "A<b>&"})
        self.assertEqual(
            addr._render_api_template("{City}", "ua", escape_values=True),
            "A&lt;b&gt;&amp;")

    # --- Поле address_display форми довідника = display-шаблон -----------------
    def test_address_display_field_uses_display_template(self):
        # «Повна адреса» на формі довідника рендериться тим самим шаблоном, що й
        # рядок на картці контакту (address_format_display).
        self.assertEqual(
            self.address.address_display,
            "%s, 01001, місто Київ, вул. Хрещатик, 1" % self.ua_name)

    # --- Дефолтний display-шаблон першого рядка картки ------------------------
    def test_default_display_template(self):
        result = self.address._render_api_template(
            self.credential.address_format_display, "ua")
        # {CityFull}/{StreetFull}; порожні поля/дужки стиснуто; область Києва
        # не дублюється (місто спецстатусу).
        self.assertEqual(
            result, "%s, 01001, місто Київ, вул. Хрещатик, 1" % self.ua_name)
        self.assertNotIn("()", result)
        self.assertNotIn("гр.", result)  # без артефакту громади

    # --- Міста спецстатусу: область не дублюється -----------------------------
    def test_special_status_city_drops_region(self):
        # Київ/Севастополь самі є регіоном (Region == City) -> область не
        # виводимо: «місто Київ», а не «місто Київ, Київ».
        out = self.address._render_api_template(
            "{Region}, {SettlementType} {City}", "ua")
        self.assertEqual(out, "місто Київ")
        self.assertNotIn("Київ, Київ", out)

    def test_regular_city_keeps_region(self):
        # Звичайне місто (область != місто) -> область ЗБЕРІГАЄТЬСЯ.
        addr = self.env["dm.geodata.address"].create({
            "region": "Сумська обл.", "city": "Суми", "settlement_type": "місто"})
        out = addr._render_api_template("{Region}, {SettlementType} {City}", "ua")
        self.assertEqual(out, "Сумська обл., місто Суми")
