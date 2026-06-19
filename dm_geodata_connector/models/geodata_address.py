import logging
import re

from markupsafe import escape

from odoo import _, api, fields, models
from odoo.tools import format_datetime

_logger = logging.getLogger(__name__)


class GeodataAddress(models.Model):
    _name = "dm.geodata.address"
    _description = "Geodata Address"
    _order = "create_date desc"

    # ПРИМІТКА: без унікальності на geodata_id. Модель строго 1:1 зі своїм
    # власником (одна приватна dm.geodata.address на партнера/сутність, ніколи не
    # спільна, без дедуплікації), тож дві сутності за однією фізичною адресою
    # мають кожна свій рядок — однакові значення geodata_id очікувані й дозволені.

    # Ключ API -> поле моделі (використовується upsert-ом, щоб знати, які поля
    # реально несе відповідь). Зберігаються лише UA + EN (рішення AUDIT).
    _FIELD_API_KEYS = {
        "geodata_id": ("ID",),
        "settlement_ref": ("SettlementId", "Id"),
        "street_ref": ("StreetId",),
        "house_ref": ("HouseId",),
        "post_index": ("Index_", "Index_8x"),
        "region": ("Region",), "region_en": ("RegionEn",),
        "area": ("Area",), "area_en": ("AreaEn",),
        "hromada": ("Hromada",), "hromada_en": ("HromadaEn",),
        "city": ("City",), "city_en": ("CityEn",),
        "settlement_type": ("SettlementType",), "settlement_type_en": ("SettlementTypeEn",),
        "city_district": ("CityDistrict",),
        "street": ("Street",), "street_en": ("StreetEn",),
        "str_type": ("StrType", "StreetType"), "str_type_en": ("StrTypeEn", "StreetTypeEn"),
        "house_num": ("HouseNum",), "house_num_add": ("HouseNumAdd",),
        "post_index_": ("Index_",),
        "koatuu": ("KOATUU",), "kato": ("KATO",), "phone_code": ("PhoneCode",),
        "is_regional_center": ("IsOCentre",), "is_district_center": ("IsRCentre",),
        "terr_status": ("TerrStatus",),
        "region_old": ("RegionOld",), "area_old": ("AreaOld",),
        "city_old": ("CityOld",), "street_old": ("StreetOld",),
        "str_type_old": ("StrTypeOld", "StreetTypeOld"),
        "latitude": ("Lat_", "Lat"), "longitude": ("Long_", "Long"),
        "latitude_settlement": ("Lat_S",), "longitude_settlement": ("Long_S",),
        "city_moniker": ("st_moniker", "Moniker"),
        "street_moniker": ("house_moniker", "str_moniker", "StrMoniker"),
    }

    name = fields.Char(compute="_compute_name", store=True)
    address_string = fields.Char(
        string="Full Address", compute="_compute_address_string", store=True
    )
    company_id = fields.Many2one(
        comodel_name="res.company",
        index=True,
        # За замовчуванням — компанія викликача як підстраховка для прямих create
        # (тести/демо); apply_address перевизначає її компанією власника, щоб адреса
        # була видима саме там, де її власник (див. _geodata_company_id).
        default=lambda self: self.env.company,
        help="Leave empty to share this address across all companies.",
    )

    # Ідентифікатори
    geodata_id = fields.Integer(string="Geodata ID", index=True)
    settlement_ref = fields.Integer(string="Settlement ID", index=True)
    street_ref = fields.Integer(string="Street ID", index=True)
    house_ref = fields.Integer(string="House ID", index=True)
    city_moniker = fields.Char(copy=False)
    street_moniker = fields.Char(copy=False)
    # Коли отримано монікер (для 15-хв реюзу без зайвого переотримання).
    city_moniker_ts = fields.Datetime(copy=False)
    street_moniker_ts = fields.Datetime(copy=False)

    # Допоміжні поля API / сирі рядки (зберігаються як отримано від API)
    source_query = fields.Char(string="Source Address")
    address_level = fields.Char()
    city_string = fields.Char()
    city_string_en = fields.Char()
    city_string_ru = fields.Char()
    street_string = fields.Char()
    house_string = fields.Char()

    # Адміністративні (UA)
    post_index = fields.Char(string="Postal Code")
    region = fields.Char(string="Region/Oblast")
    area = fields.Char(string="District/Raion")
    hromada = fields.Char(string="Territorial Community")
    city = fields.Char(string="Settlement")
    suburb = fields.Char()
    settlement_type = fields.Char(string="Settlement Type")
    city_district = fields.Char(string="Settlement District")
    street = fields.Char(string="Street Name")
    str_type = fields.Char(string="Street Type")
    house_num = fields.Char(string="House Number")
    house_num_add = fields.Char(string="House Number Addition")

    # Англійська транслітерація
    region_en = fields.Char(string="Region (EN)")
    area_en = fields.Char(string="District/Raion (EN)")
    hromada_en = fields.Char(string="Territorial Community (EN)")
    city_en = fields.Char(string="Settlement (EN)")
    settlement_type_en = fields.Char(string="Settlement Type (EN)")
    city_district_en = fields.Char(string="Settlement District (EN)")
    street_en = fields.Char(string="Street Name (EN)")
    str_type_en = fields.Char(string="Street Type (EN)")
    house_num_add_en = fields.Char(string="House Number Addition (EN)")

    # Російський переклад (зберігається як отримано; поки не показується/не запитується)
    region_ru = fields.Char()
    area_ru = fields.Char()
    hromada_ru = fields.Char()
    city_ru = fields.Char()
    settlement_type_ru = fields.Char()
    city_district_ru = fields.Char()
    street_ru = fields.Char()
    str_type_ru = fields.Char()
    house_num_add_ru = fields.Char()

    # Старі назви (UA + EN + RU)
    region_old = fields.Char(string="Old Region")
    region_old_en = fields.Char(string="Old Region (EN)")
    region_old_ru = fields.Char()
    area_old = fields.Char(string="Old District")
    area_old_en = fields.Char(string="Old District (EN)")
    area_old_ru = fields.Char()
    hromada_old = fields.Char(string="Old Hromada")
    hromada_old_en = fields.Char(string="Old Hromada (EN)")
    hromada_old_ru = fields.Char()
    suburb_old = fields.Char(string="Old Suburb")
    city_old = fields.Char(string="Old Settlement Name")
    city_old_en = fields.Char(string="Old Settlement Name (EN)")
    city_old_ru = fields.Char()
    settlement_type_old = fields.Char(string="Old Settlement Type")
    settlement_type_old_en = fields.Char(string="Old Settlement Type (EN)")
    settlement_type_old_ru = fields.Char()
    street_old = fields.Char(string="Old Street Name")
    street_old_en = fields.Char(string="Old Street Name (EN)")
    street_old_ru = fields.Char()
    str_type_old = fields.Char(string="Old Street Type")
    str_type_old_en = fields.Char(string="Old Street Type (EN)")
    str_type_old_ru = fields.Char()

    # Метро
    metro_station = fields.Char(string="Metro Station")
    metro_line = fields.Char(string="Metro Line")
    metro_distance = fields.Char(string="Metro Distance")

    # Коди / гео
    koatuu = fields.Char(string="KOATUU")
    kato = fields.Char(string="KATOTTG")
    phone_code = fields.Char(string="Phone Code")
    is_regional_center = fields.Boolean(string="Regional Center")
    is_district_center = fields.Boolean(string="District Center")
    terr_status = fields.Char(string="Territory Status")
    latitude = fields.Float(string="Latitude", digits=(10, 7))
    longitude = fields.Float(string="Longitude", digits=(10, 7))
    latitude_settlement = fields.Float(string="Settlement Latitude", digits=(10, 7))
    longitude_settlement = fields.Float(string="Settlement Longitude", digits=(10, 7))

    # Додатково
    comments = fields.Text(string="Comments")
    description = fields.Text(string="Description")

    # Сирі відповіді API, збережені дослівно по мові ("ua"/"en"), злиті по ланцюгу
    # місто->вулиця->будинок. Гарантує, що ЖОДНЕ поле з відповіді API не втрачається,
    # навіть нові/недокументовані, що ще не мають окремої колонки.
    api_payload = fields.Json(string="Raw API payload", copy=False)

    # Формати для документів / листів (UA + EN)
    address_ua_postal = fields.Char(compute="_compute_address_formats", store=True)
    address_ua_short = fields.Char(compute="_compute_address_formats", store=True)
    address_full_ua = fields.Char(string="Full Address (UA)", compute="_compute_full_addresses", store=True)
    address_full_en = fields.Char(string="Full Address (EN)", compute="_compute_full_addresses", store=True)
    address_letter_ua = fields.Char(string="Letter Address (UA)", compute="_compute_full_addresses", store=True)
    address_letter_en = fields.Char(string="Letter Address (EN)", compute="_compute_full_addresses", store=True)

    _NAME_DEPENDS = (
        "region", "area", "hromada", "settlement_type", "city",
        "str_type", "street", "house_num", "house_num_add",
        "street_old", "str_type_old", "city_old", "area_old",
    )

    # ------------------------------------------------------------------
    # Обчислення (store=True). Форматувальники приймають credential як параметр —
    # ніколи не викликати get_credential() на кожен запис у циклі (AUDIT #7).
    # ------------------------------------------------------------------
    @api.depends(*_NAME_DEPENDS)
    def _compute_name(self):
        for rec in self:
            rec.name = rec._rebuild_address_string() or _("New Address")

    @api.depends(*_NAME_DEPENDS)
    def _compute_address_string(self):
        for rec in self:
            rec.address_string = rec._rebuild_address_string() or False

    @api.depends("post_index", "region", "area", "hromada", "settlement_type",
                 "city", "str_type", "street", "house_num", "house_num_add")
    def _compute_address_formats(self):
        for rec in self:
            rec.address_ua_postal = rec._format_postal("ua")
            rec.address_ua_short = rec._format_short("ua")

    @api.depends("post_index", "region", "area", "hromada", "settlement_type",
                 "city", "str_type", "street", "house_num", "house_num_add",
                 "region_en", "area_en", "hromada_en", "settlement_type_en",
                 "city_en", "str_type_en", "street_en", "house_num_add_en",
                 "region_old", "area_old", "hromada_old", "settlement_type_old",
                 "city_old", "str_type_old", "street_old", "suburb_old",
                 "region_old_en", "area_old_en", "hromada_old_en",
                 "settlement_type_old_en", "city_old_en", "str_type_old_en",
                 "street_old_en",
                 # Додаткові поля, які можна вживати у шаблонах документів/конвертів.
                 "city_district", "suburb", "suburb_old",
                 "kato", "koatuu", "phone_code", "terr_status",
                 "metro_station", "metro_line", "metro_distance", "write_date")
    def _compute_full_addresses(self):
        credential = self.env["dm.geodata.api.credential"].sudo().get_credential()
        store_en = credential.store_english if credential else True
        for rec in self:
            rec.address_full_ua = rec._format_full_address("ua", credential)
            rec.address_letter_ua = rec._format_letter_address("ua", credential)
            if store_en:
                rec.address_full_en = rec._format_full_address("en", credential)
                rec.address_letter_en = rec._format_letter_address("en", credential)
            else:
                rec.address_full_en = False
                rec.address_letter_en = False

    # ------------------------------------------------------------------
    # Допоміжні форматувальники
    # ------------------------------------------------------------------
    def _field_lang(self, field_name, lang):
        self.ensure_one()
        if lang == "en":
            value = self[field_name + "_en"] if (field_name + "_en") in self._fields else False
            return value or self[field_name] or ""
        return self[field_name] or ""

    def _city_part(self, lang):
        city = self._field_lang("city", lang)
        if not city:
            return ""
        stype = self._field_lang("settlement_type", lang)
        return ("%s %s" % (stype, city)).strip() if stype else city

    def _street_part(self, lang):
        street = self._field_lang("street", lang)
        if not street:
            return ""
        stype = self._field_lang("str_type", lang)
        return ("%s %s" % (stype, street)).strip() if stype else street

    @staticmethod
    def _typed_display(name, type_cur, name_old, type_old):
        """Display of a typed level (settlement / street) with the historical
        "(old)" part. "old" covers BOTH the name and the type:
        - old name present  -> "<type> <name> (<old_type> <old_name>)" (parens at end);
        - only the type changed -> "<type> (<old_type>) <name>" (parens after the type)."""
        if not name:
            return ""
        if not name_old and type_old and type_old != (type_cur or ""):
            head = "%s (%s)" % (type_cur, type_old) if type_cur else "(%s)" % type_old
            return ("%s %s" % (head, name)).strip()
        base = ("%s %s" % (type_cur, name)).strip() if type_cur else name
        if name_old:
            old_full = ("%s %s" % (type_old, name_old)).strip() if type_old else name_old
            return "%s (%s)" % (base, old_full)
        return base

    def _city_old_display(self, lang="ua"):
        """Old settlement name only when it is a genuine rename — NOT merely an old
        administrative subordination. Per the source rule, CityOld counts as a real
        old name only when there is no old suburb (SuburbOld empty) and it actually
        differs from the current name; otherwise it is suppressed everywhere."""
        self.ensure_one()
        # Заповнене suburb_old означає стару адмінпідпорядкованість, а не
        # перейменування — стару назву міста в такому разі не показуємо.
        if self.suburb_old:
            return ""
        old = self._field_lang("city_old", lang)
        if not old or old == self._field_lang("city", lang):
            return ""
        return old

    def _city_display(self, lang, show_old=False):
        return self._typed_display(
            self._field_lang("city", lang),
            self._field_lang("settlement_type", lang),
            self._city_old_display(lang) if show_old else "",
            self._field_lang("settlement_type_old", lang) if show_old else "")

    def _street_display(self, lang, show_old=False):
        return self._typed_display(
            self._field_lang("street", lang),
            self._field_lang("str_type", lang),
            self._field_lang("street_old", lang) if show_old else "",
            self._field_lang("str_type_old", lang) if show_old else "")

    @staticmethod
    def _with_old(current, old):
        """Append the historical name in parentheses: "Current (Old)"."""
        if not old:
            return current
        return "%s (%s)" % (current, old) if current else old

    @staticmethod
    def _hromada_suffix(value, lang="ua"):
        """Append the 'громада' abbreviation to a hromada name. The API returns the
        hromada bare (unlike region/area, which already carry 'обл.'/'р-н'), so we
        add it at display time: UA 'гр.', EN 'gr.'."""
        if not value:
            return value
        return "%s %s" % (value, "gr." if lang == "en" else "гр.")

    def _hromada_full_display(self, lang="ua"):
        """Громада з суфіксом «гр.» і старою назвою в дужках: «Сумська гр.
        (Стара гр.)»; лише поточна — «Сумська гр.»; порожньо — «» (без артефакту
        «гр.»)."""
        cur = self._hromada_suffix(self._field_lang("hromada", lang), lang)
        old = self._hromada_suffix(self._field_lang("hromada_old", lang), lang)
        if cur and old:
            return "%s (%s)" % (cur, old)
        if cur:
            return cur
        return "(%s)" % old if old else ""

    def _house_part(self, lang="ua"):
        house = self.house_num or ""
        # Літерний суфікс номера будинку залежить від мови (напр. "Д" / "d").
        add = self._field_lang("house_num_add", lang) if house else ""
        return "%s%s" % (house, add) if house and add else house

    def _collect_parts(self, lang, show_old=False):
        self.ensure_one()
        parts = []
        if self.post_index:
            parts.append(self.post_index)
        city = self._city_display(lang, show_old)
        region = self._field_lang("region", lang)
        if show_old:
            region = self._with_old(region, self._field_lang("region_old", lang))
        if region and region not in city:
            parts.append(region)
        area = self._field_lang("area", lang)
        if show_old:
            area = self._with_old(area, self._field_lang("area_old", lang))
        if area and area not in city:
            parts.append(area)
        if city:
            parts.append(city)
        street = self._street_display(lang, show_old)
        house = self._house_part(lang)
        if street and house:
            parts.append("%s, %s" % (street, house))
        elif street or house:
            parts.append(street or house)
        return parts

    # ------------------------------------------------------------------
    # Уніфікований рушій шаблонів адрес (документи, конверти, колонки «Деталі»,
    # поля адресного блоку). Імена плейсхолдерів = імена полів API; ЗНАЧЕННЯ —
    # сирі, зі збережених (очищуваних) колонок через мапу APIKey->колонка, БЕЗ
    # авто-склейок. Склейку робить лише сам шаблон (вільний текст + сусідні поля).
    # ------------------------------------------------------------------
    # APIKey (як у відповіді API) -> базове поле моделі. Для EN значення береться
    # з відповідного `_en` поля з відкатом на UA (через _field_lang).
    _API_TEMPLATE_FIELDS = {
        "Index_": "post_index",
        "Region": "region", "Area": "area", "Hromada": "hromada",
        "City": "city", "Suburb": "suburb",
        "SettlementType": "settlement_type", "CityDistrict": "city_district",
        "Street": "street", "StrType": "str_type",
        "HouseNum": "house_num", "HouseNumAdd": "house_num_add",
        "KOATUU": "koatuu", "KATO": "kato", "PhoneCode": "phone_code",
        "TerrStatus": "terr_status",
        "IsOCentre": "is_regional_center", "IsRCentre": "is_district_center",
        "RegionOld": "region_old", "AreaOld": "area_old",
        "HromadaOld": "hromada_old", "SuburbOld": "suburb_old",
        "CityOld": "city_old", "SettlementTypeOld": "settlement_type_old",
        "StreetOld": "street_old", "StrTypeOld": "str_type_old",
        "MetroStation": "metro_station", "MetroLine": "metro_line",
        "MetroDistance": "metro_distance",
        "Lat_": "latitude", "Long_": "longitude",
        "Lat_S": "latitude_settlement", "Long_S": "longitude_settlement",
        "CityString": "city_string", "StreetString": "street_string",
        "HouseString": "house_string",
    }

    # Кольори ліній метро (офіційні кольори ліній) для бейджа лінії у колонці
    # «Деталі адреси». Ключі = точні рядки MetroLine з API. Невідома лінія ->
    # сірий (#555); порожня лінія (Дніпро/не-метро) -> бейдж без фону (невидимий).
    _METRO_LINE_COLORS = {
        # Київ
        "Святошинсько-Броварська": "#D52B1E",  # червона
        "Оболонсько-Теремківська": "#0057B8",  # синя
        "Сирецько-Печерська": "#009739",       # зелена
        # Харків
        "Холодногірсько-Заводська": "#D52B1E",  # червона
        "Салтівська": "#0057B8",                # синя
        "Олексіївська": "#009739",              # зелена
        # Дніпро
        "Центральна": "#FF8C00",                # помаранчева
    }

    _PLACEHOLDER_RE = re.compile(r"\{(\w+)\}")
    # Парний фрагмент у дужках () [] «» (без вкладеності): якщо містить
    # плейсхолдер(и) і ВСІ вони порожні — увесь фрагмент (з текстом усередині)
    # прибирається; напр. "(на дату {updated})" зникає за порожнього {updated}.
    _GROUP_RE = re.compile(r"\(([^()]*)\)|\[([^\[\]]*)\]|«([^«»]*)»")
    _SENTINEL = "\x00"  # маркер порожнього плейсхолдера (для стискання роздільників)

    @staticmethod
    def _template_str(value):
        if value in (None, False, ""):
            return ""
        if value is True:
            return _("Yes")
        if isinstance(value, float):
            return ("%g" % value) if value else ""
        return str(value)

    def _api_template_values(self, lang="ua", extra=None):
        """{placeholder: рядок} для рушія. Імена = ключі API; значення сирі з
        очищуваних колонок (EN із відкатом на UA). Плюс синтетичні country/updated
        та `extra` (Odoo-поля власника)."""
        self.ensure_one()
        values = {api_key: self._template_str(self._field_lang(field, lang))
                  for api_key, field in self._API_TEMPLATE_FIELDS.items()}
        # Розумне відображення населеного пункту/вулиці зі старими назвами:
        # «село Іванівка (селище Калинівка)» при зміні назви; «село (селище)
        # Іванівка» коли змінився лише тип (логіка _typed_display).
        values["CityFull"] = self._city_display(lang, show_old=True)
        values["StreetFull"] = self._street_display(lang, show_old=True)
        values["HromadaFull"] = self._hromada_full_display(lang)
        # Місто спецстатусу (Київ/Севастополь) саме є регіоном — не дублюємо
        # область у текстових шаблонах ("місто Київ, Київ" -> "місто Київ").
        # Узгоджено з _collect_parts: той самий тест "region in city".
        region_val = self._field_lang("region", lang)
        if region_val and region_val in self._city_display(lang, show_old=True):
            values["Region"] = ""
            values["RegionOld"] = ""
        # Колір бейджа лінії метро (колонки рендеряться з lang="ua", тож ключ
        # беремо з UA-назви лінії). Порожня лінія -> "" (бейдж без фону).
        values["MetroLineColor"] = (
            self._METRO_LINE_COLORS.get(self.metro_line, "#555")
            if self.metro_line else "")
        values["country"] = {"ua": "УКРАЇНА", "en": "Ukraine"}.get(lang, "Ukraine")
        values["updated"] = (format_datetime(self.env, self.write_date)
                             if self.write_date else "")
        if extra:
            values.update({k: self._template_str(v) for k, v in extra.items()})
        return values

    def _render_api_template(self, template, lang="ua", extra=None,
                             escape_values=False):
        """Порядковий рендер: підстановка {APIKey}->сире значення зі збереженням
        вільного тексту; порожні плейсхолдери прибираються разом із суміжними
        роздільниками; рядок із плейсхолдерами, що став порожнім, пропускається
        (вільний текст без плейсхолдерів зберігається). Один рушій для
        однорядкових (кома-список без «дірок») і багаторядкових шаблонів.

        `escape_values=True` (для HTML-колонок) екранує підставлені значення, а
        літерал шаблону лишає як є — щоб адмінська розмітка рендерилась, а дані
        API не могли інʼєктувати HTML."""
        self.ensure_one()
        if not template:
            return ""
        values = self._api_template_values(lang, extra)
        if escape_values:
            values = {k: (str(escape(v)) if v else v) for k, v in values.items()}
        out = []
        for line in template.splitlines():
            keys = self._PLACEHOLDER_RE.findall(line)
            if keys and not any(values.get(k) for k in keys):
                continue  # усі плейсхолдери рядка порожні -> ховаємо рядок
            out.append(self._render_template_line(line, values))
        return "\n".join(out).strip("\n")

    def _subst_squeeze(self, text, values):
        """Підстановка {X}->значення зі стисканням порожніх полів: порожній
        плейсхолдер прибирається разом із суміжним роздільником; залишкові
        пробіли/коми нормалізуються."""
        text = self._PLACEHOLDER_RE.sub(
            lambda m: values.get(m.group(1)) or self._SENTINEL, text)
        text = re.sub(r"\s*[,;|/]?\s*" + self._SENTINEL, "", text)
        text = text.replace(self._SENTINEL, "")
        text = re.sub(r"\s{2,}", " ", text)
        text = re.sub(r"\s+([,;])", r"\1", text)
        text = re.sub(r"([,;])\s*(?:[,;]\s*)+", r"\1 ", text)
        return text

    def _render_template_line(self, line, values):
        """Рендер одного рядка:
        1) груповий прохід — фрагмент у () [] «»: без плейсхолдерів лишається; з
           плейсхолдерами, усі з яких порожні, прибирається повністю; інакше дужки
           + підстановка всередині;
        2) підстановка решти {X} зі стисканням порожніх полів;
        3) обрізати роздільники по краях."""
        def _group(m):
            inner = next(g for g in m.groups() if g is not None)
            op, cl = m.group(0)[0], m.group(0)[-1]
            keys = self._PLACEHOLDER_RE.findall(inner)
            if not keys:
                return m.group(0)  # літеральні дужки без плейсхолдерів -> лишаємо
            if not any(values.get(k) for k in keys):
                return ""  # усі плейсхолдери фрагмента порожні -> прибрати весь
            return "%s%s%s" % (op, self._subst_squeeze(inner, values).strip(), cl)

        line = self._GROUP_RE.sub(_group, line)
        line = self._subst_squeeze(line, values)
        # Обрізаємо хвостову `;` лише ліворуч, а не праворуч: інакше зрізалася б
        # `;`, що завершує HTML-entity (`&amp;`/`&lt;`…) наприкінці рядка. Внутрішні
        # роздільники й так стискає _subst_squeeze.
        return line.lstrip(" ,;|/\t").rstrip(" ,|/\t")

    def _template_credential(self):
        return self.env["dm.geodata.api.credential"].sudo().get_credential()

    def _template_or_default(self, credential, fname):
        """Шаблон поля credential, або його дефолт (щоб композиція адреси
        працювала навіть без налаштованого credential). Дефолт беремо через
        default_get (Field.default — callable, тож читати його напряму не можна)."""
        if credential and credential[fname]:
            return credential[fname]
        default = self.env["dm.geodata.api.credential"].default_get([fname])
        return default.get(fname) or ""

    def _format_full_address(self, lang="ua", credential=None):
        self.ensure_one()
        credential = credential or self._template_credential()
        return self._render_api_template(
            self._template_or_default(credential, "address_format_document"), lang)

    def _format_letter_address(self, lang="ua", credential=None):
        self.ensure_one()
        credential = credential or self._template_credential()
        return self._render_api_template(
            self._template_or_default(credential, "address_format_letter"), lang)

    def _format_postal(self, lang="ua"):
        return ", ".join(self._collect_parts(lang))

    def _format_short(self, lang="ua"):
        self.ensure_one()
        parts = []
        city = self._city_part(lang)
        if city:
            parts.append(city)
        street = self._street_part(lang)
        house = self._house_part(lang)
        if street and house:
            parts.append("%s, %s" % (street, house))
        elif street or house:
            parts.append(street or house)
        return ", ".join(parts)

    def _rebuild_address_string(self):
        self.ensure_one()
        parts = []
        city = self._city_part("ua")
        if self.region and self.region not in city:
            parts.append(self.region)
        if self.area and self.area not in city:
            parts.append(self.area)
        if city:
            parts.append(city)
        street = self._street_part("ua")
        if street:
            parts.append(street)
        house = self._house_part()
        if house:
            parts.append(house)
        return ", ".join(parts)

    # ------------------------------------------------------------------
    # Інгестія API (БЕЗ зовнішнього HTTP тут — AUDIT #5)
    # ------------------------------------------------------------------
    @staticmethod
    def _to_float(value):
        try:
            return float(value)
        except (TypeError, ValueError):
            return None

    @api.model
    def _api_data_to_vals(self, api_data):
        get = api_data.get
        # Координати (#4): координати будинку лише коли payload несе будинок/вулицю;
        # інакше Lat/Long описують центр населеного пункту. Відсутні координати ->
        # None (пропущено), тож злиття ніколи не стирає попередні значення (напр.
        # крок Houses не має Lat_S, тож координати населеного пункту зберігаються).
        has_building = bool(get("HouseNum") or get("HouseId") or get("Street"))
        lat_b = self._to_float(get("Lat_") or get("Lat")) if has_building else None
        long_b = self._to_float(get("Long_") or get("Long")) if has_building else None
        lat_s = self._to_float(get("Lat_S"))
        long_s = self._to_float(get("Long_S"))
        if lat_s is None and not has_building:
            lat_s = self._to_float(get("Lat_") or get("Lat"))
        if long_s is None and not has_building:
            long_s = self._to_float(get("Long_") or get("Long"))
        vals = {
            "geodata_id": get("ID"),
            "settlement_ref": get("SettlementId") or get("Id"),
            "street_ref": get("StreetId"),
            "house_ref": get("HouseId"),
            "source_query": get("SourceAddress") or get("AddressString"),
            "address_level": get("AddressLevel"),
            "post_index": get("Index_") or get("Index_8x"),
            "city_string": get("CityString"),
            "city_string_en": get("CityStringEn"),
            "city_string_ru": get("CityStringRu"),
            "street_string": get("StreetString"),
            "house_string": get("HouseString"),
            "region": get("Region"), "region_en": get("RegionEn"), "region_ru": get("RegionRu"),
            "area": get("Area"), "area_en": get("AreaEn"), "area_ru": get("AreaRu"),
            "hromada": get("Hromada"), "hromada_en": get("HromadaEn"), "hromada_ru": get("HromadaRu"),
            "city": get("City"), "city_en": get("CityEn"), "city_ru": get("CityRu"),
            "suburb": get("Suburb"),
            "settlement_type": get("SettlementType"),
            "settlement_type_en": get("SettlementTypeEn"),
            "settlement_type_ru": get("SettlementTypeRu"),
            "city_district": get("CityDistrict"),
            "city_district_en": get("CityDistrictEn"),
            "city_district_ru": get("CityDistrictRu"),
            "street": get("Street"), "street_en": get("StreetEn"), "street_ru": get("StreetRu"),
            "str_type": get("StrType") or get("StreetType"),
            "str_type_en": get("StrTypeEn") or get("StreetTypeEn"),
            "str_type_ru": get("StrTypeRu") or get("StreetTypeRu"),
            "house_num": get("HouseNum"), "house_num_add": get("HouseNumAdd"),
            "house_num_add_en": get("HouseNumAddEn"),
            "house_num_add_ru": get("HouseNumAddRu"),
            "koatuu": get("KOATUU"), "kato": get("KATO"), "phone_code": get("PhoneCode"),
            "is_regional_center": get("IsOCentre"),
            "is_district_center": get("IsRCentre"),
            "terr_status": get("TerrStatus"),
            "region_old": get("RegionOld"),
            "region_old_en": get("RegionOldEn"), "region_old_ru": get("RegionOldRu"),
            "area_old": get("AreaOld"), "area_old_en": get("AreaOldEn"), "area_old_ru": get("AreaOldRu"),
            "hromada_old": get("HromadaOld"),
            "hromada_old_en": get("HromadaOldEn"), "hromada_old_ru": get("HromadaOldRu"),
            "suburb_old": get("SuburbOld"),
            "city_old": get("CityOld"), "city_old_en": get("CityOldEn"), "city_old_ru": get("CityOldRu"),
            "settlement_type_old": get("SettlementTypeOld"),
            "settlement_type_old_en": get("SettlementTypeOldEn"),
            "settlement_type_old_ru": get("SettlementTypeOldRu"),
            "street_old": get("StreetOld"), "street_old_en": get("StreetOldEn"), "street_old_ru": get("StreetOldRu"),
            "str_type_old": get("StrTypeOld") or get("StreetTypeOld"),
            "str_type_old_en": get("StrTypeOldEn") or get("StreetTypeOldEn"),
            "str_type_old_ru": get("StrTypeOldRu") or get("StreetTypeOldRu"),
            "metro_station": get("MetroStation") or get("MetroName"),
            "metro_line": get("MetroLine"), "metro_distance": get("MetroDistance"),
            "comments": get("Comments"), "description": get("Description"),
            "latitude": lat_b, "longitude": long_b,
            "latitude_settlement": lat_s, "longitude_settlement": long_s,
            "city_moniker": get("st_moniker") or get("Moniker") or None,
            "street_moniker": (get("house_moniker") or get("str_moniker")
                               or get("StrMoniker") or None),
        }
        vals = {k: v for k, v in vals.items() if v is not None}
        # Мітка часу отримання монікера (для 15-хв реюзу).
        now = fields.Datetime.now()
        if vals.get("city_moniker"):
            vals["city_moniker_ts"] = now
        if vals.get("street_moniker"):
            vals["street_moniker_ts"] = now
        return vals

    # Поля нижчих рівнів, що очищуються при (пере)виборі вищого рівня (clear-down).
    _CLEAR_BELOW_CITY = (
        "street", "str_type", "street_en", "str_type_en", "street_ru", "str_type_ru",
        "street_old", "str_type_old", "street_old_en", "str_type_old_en",
        "street_old_ru", "str_type_old_ru", "street_string",
        "house_num", "house_num_add", "house_num_add_en", "house_num_add_ru",
        "house_string", "street_ref", "house_ref",
        "street_moniker", "latitude", "longitude",
        # Район міста і метро — нижчого рівня (вулиця/будинок); при перевиборі
        # міста старі значення не мають «прилипати».
        "city_district", "city_district_en", "city_district_ru",
        "metro_station", "metro_line", "metro_distance",
    )
    _CLEAR_BELOW_STREET = (
        "house_num", "house_num_add", "house_num_add_en", "house_num_add_ru",
        "house_string", "house_ref", "latitude", "longitude",
        "city_district", "city_district_en", "city_district_ru",
        "metro_station", "metro_line", "metro_distance",
    )
    # Опційні поля рівня, що СКИДАЮТЬСЯ, коли payload (пере)визначає цей рівень на
    # перевикористаному записі: відсутній у відповіді ключ означає «його немає»,
    # тож стара назва (район/громада) попередньої адреси не «прилипає». EN-варіанти
    # (`*_old_en`) керує fetch_en_translit (повний перезапис); тут — UA/RU.
    _SETTLEMENT_RESET = (
        # Поштовий індекс прив'язаний до вулиці/будинку, тож при (пере)виборі
        # населеного пункту скидаємо його, щоб старий індекс попередньої адреси
        # не «прилипав» (повна адреса несе свій Index_ і зберігає його через
        # vals.setdefault).
        "post_index",
        # Коди/статус рівня населеного пункту: city-payload несе їх, тож при
        # перевиборі міста без статусу/коду старе значення не «прилипає».
        "terr_status", "kato", "koatuu", "phone_code",
        "is_regional_center", "is_district_center",
        "area", "area_ru", "hromada", "hromada_ru", "suburb",
        "region_old", "region_old_ru", "area_old", "area_old_ru",
        "hromada_old", "hromada_old_ru", "suburb_old",
        "city_old", "city_old_ru",
        "settlement_type_old", "settlement_type_old_ru",
    )
    _STREET_RESET = ("street_old", "street_old_ru", "str_type_old", "str_type_old_ru")
    _HOUSE_RESET = ("house_num_add", "house_num_add_ru",
                    "city_district", "city_district_ru",
                    "metro_station", "metro_line", "metro_distance")

    @staticmethod
    def _api_level(api_data):
        """Hierarchy level carried by a payload: 'house' / 'street' / 'city'."""
        if api_data.get("HouseId") or api_data.get("HouseNum"):
            return "house"
        if api_data.get("StreetId") or api_data.get("Street"):
            return "street"
        return "city"

    def update_from_api(self, api_data):
        """Merge an API payload into THIS existing address (no create, no HTTP).

        Provided fields are written; lower levels are cleared when a higher
        level is (re)selected (clear-down, fix #4) so the chain stays
        consistent (e.g. picking a new city drops the previous street/house).
        Used by the city->street->house chain so a partner keeps ONE
        dm.geodata.address (AUDIT #12 / test #8).
        """
        self.ensure_one()
        if not isinstance(api_data, dict):
            return self
        get = api_data.get
        vals = self._api_data_to_vals(api_data)
        # Рівневий ресет: payload, що несе ідентичність рівня, ПОВНІСТЮ визначає
        # його опційні поля — відсутні ключі чистимо (інакше стара назва від
        # попередньої адреси лишається на перевикористаному записі). Працює і для
        # повної адреси (несе City+Street+House одразу), де clear-below не діяв.
        def _reset(fields):
            for fname in fields:
                vals.setdefault(fname, False)
        if get("City"):
            _reset(self._SETTLEMENT_RESET)
        if get("Street"):
            _reset(self._STREET_RESET)
        if get("HouseNum") or get("HouseId"):
            _reset(self._HOUSE_RESET)
        level = self._api_level(api_data)
        clear = ()
        if level == "city":
            clear = self._CLEAR_BELOW_CITY
        elif level == "street":
            clear = self._CLEAR_BELOW_STREET
        for fname in clear:
            if fname not in vals:
                vals[fname] = 0.0 if fname in ("latitude", "longitude") else False
        if vals:
            self.write(vals)
        self._merge_raw(api_data, "ua")
        return self

    @api.model
    def create_from_api(self, api_data):
        """Create a NEW dm.geodata.address from an API payload. Pure DB work - no
        HTTP (AUDIT #5). Must be called from a sudo service layer (AUDIT #1).

        No deduplication / no reuse: the model is strictly 1:1 with its owner,
        so every selection for an owner without a linked address creates its own
        private row (see dm.geodata.address.mixin.apply_address).
        """
        if not isinstance(api_data, dict):
            return self.browse()
        record = self.create(self._api_data_to_vals(api_data))
        record._merge_raw(api_data, "ua")
        return record

    def _merge_raw(self, api_data, lang):
        """Keep the raw API response verbatim in `api_payload[lang]` (merged
        across the chain), so nothing the API returns is ever lost - even
        new/undocumented keys with no dedicated column."""
        if not isinstance(api_data, dict) or not api_data:
            return
        self.ensure_one()
        payload = dict(self.api_payload or {})
        bucket = dict(payload.get(lang) or {})
        bucket.update(api_data)
        payload[lang] = bucket
        self.api_payload = payload

    # ------------------------------------------------------------------
    # Англійська транслітерація (синхронно, лише на вимогу — AUDIT #5)
    # ------------------------------------------------------------------
    # Кожна колонка `_en` -> ключ(і) API, що несуть її транслітероване значення у
    # відповіді lang=en. Керує повним (не частковим) захопленням EN нижче.
    _EN_API_KEYS = {
        "region_en": ("Region",),
        "area_en": ("Area",),
        "hromada_en": ("Hromada",),
        "city_en": ("City",),
        "settlement_type_en": ("SettlementType",),
        "city_district_en": ("CityDistrict",),
        "street_en": ("Street",),
        "str_type_en": ("StrType", "StreetType"),
        "house_num_add_en": ("HouseNumAdd",),
        "city_string_en": ("CityString",),
        "region_old_en": ("RegionOld",),
        "area_old_en": ("AreaOld",),
        "hromada_old_en": ("HromadaOld",),
        "settlement_type_old_en": ("SettlementTypeOld",),
        "city_old_en": ("CityOld",),
        "street_old_en": ("StreetOld",),
        "str_type_old_en": ("StrTypeOld", "StreetTypeOld"),
    }

    def fetch_en_translit(self, credential):
        """Fetch EN transliteration for this address from the API. Called
        once at on_select time, never inside create()/compute.

        Captures ALL `_en` columns the response carries (including the house
        suffix, settlement district and old names), not just a hand-picked few.

        The whole `_en` set is rewritten EVERY time (missing keys -> False), so a
        reused address record never keeps a previous address's transliteration:
        otherwise, when a new selection's EN response omits a field (e.g. a city
        without a district) or the EN call fails/returns nothing, the stale `_en`
        would survive and `address_full_en` would show a DIFFERENT address than
        `address_full_ua` (and re-saving would not fix it, since it just recomputes
        from the stale `_en`). On an empty/failed EN response every `_en` is
        cleared, so EN gracefully falls back to the UA value (same address, just
        not transliterated) instead of lingering on the old one.
        """
        self.ensure_one()
        if self.env.context.get("geodata_skip_translit") or not credential:
            return
        if not credential.store_english:
            return
        query = self._rebuild_address_string()
        if not query:
            return
        results = credential.api_address(query, lang="en_US")
        data = results[0] if results else {}
        # ПОВНИЙ набір _en: відсутні у відповіді ключі -> False (очищення), щоб не
        # лишився сегмент попередньої адреси. Порожня відповідь -> усі _en чистяться.
        vals = {field: next((data.get(k) for k in keys if data.get(k)), False)
                for field, keys in self._EN_API_KEYS.items()}
        if data:
            self._merge_raw(data, "en")
        self.with_context(geodata_skip_translit=True).write(vals)

    # ------------------------------------------------------------------
    # Відображення значень на боці партнера
    # ------------------------------------------------------------------
    @staticmethod
    def _normalize_region_name(region):
        """Strip the oblast suffix so 'Миколаївська обл.' matches the synced
        res.country.state name 'Миколаївська'."""
        text = (region or "").strip()
        for suffix in (" область", " обл.", " обл", " oblast"):
            if text.lower().endswith(suffix):
                return text[: -len(suffix)].strip()
        return text

    def _resolve_state_id(self):
        """Resolve the res.country.state for this record's region (Ukraine).

        Search only - never create (states are synced at install, AUDIT #10).
        """
        self.ensure_one()
        if not self.region:
            return False
        country = self.env.ref("base.ua", raise_if_not_found=False)
        if not country:
            return False
        name = self._normalize_region_name(self.region)
        State = self.env["res.country.state"].sudo()
        state = State.search(
            [("country_id", "=", country.id), ("name", "=", name)], limit=1
        ) or State.search(
            [("country_id", "=", country.id), ("name", "ilike", name)], limit=1
        )
        return state.id if state else False

    def to_address_values(self):
        """Return standard partner address fields derived from this record.

        City / Street (1) / Street 2 are rendered from the configurable block
        templates (`block_format_city` / `_street` / `_street2`) using raw API
        values 1:1 (no auto-merge); the user controls composition via the
        templates. Area/Hromada stay as raw values (kept for internal use)."""
        self.ensure_one()
        credential = self._template_credential()
        city = self._render_api_template(
            self._template_or_default(credential, "block_format_city"), "ua")
        street = self._render_api_template(
            self._template_or_default(credential, "block_format_street"), "ua")
        street2 = self._render_api_template(
            self._template_or_default(credential, "block_format_street2"), "ua")
        area = self._render_api_template(
            self._template_or_default(credential, "block_format_area"), "ua")
        hromada = self._render_api_template(
            self._template_or_default(credential, "block_format_hromada"), "ua")
        country = self.env.ref("base.ua", raise_if_not_found=False)
        return {
            "street": street or False,
            "street2": street2 or False,
            "city": city or False,
            "zip": self.post_index or False,
            "state_id": self._resolve_state_id(),
            "area": area or False,
            "hromada": hromada or False,
            "country_id": country.id if country else False,
            "partner_latitude": self.latitude or self.latitude_settlement or 0.0,
            "partner_longitude": self.longitude or self.longitude_settlement or 0.0,
        }
