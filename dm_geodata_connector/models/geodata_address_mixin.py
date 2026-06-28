import logging
import re
from datetime import timedelta

from markupsafe import Markup

from odoo import _, api, fields, models
from odoo.exceptions import AccessError

_logger = logging.getLogger(__name__)

# Монікери API живуть ~15 хв — у межах цього вікна збережений монікер реюзимо
# (без зайвого переотримання через API Cities/Streets).
_MONIKER_TTL = timedelta(minutes=15)

# Кінцевий токен будинку наприкінці запиту вулиці, напр. "вул. Шевченка, 12А".
_HOUSE_TAIL_RE = re.compile(r"[,\s]+(\d[\w\-/]*)\s*$")


class GeodataAddressMixin(models.AbstractModel):
    _name = "dm.geodata.address.mixin"
    _description = "Geodata Address Mixin"

    geodata_address_id = fields.Many2one(
        comodel_name="dm.geodata.address",
        string="Geodata Address",
        ondelete="set null",
        copy=False,
    )
    geodata_autocomplete_active = fields.Boolean(store=False, default=False)
    # Ланцюг monikers тримається на власнику як ТРАНЗИТИВНИЙ (незбережений) стан
    # форми, щоб JS-віджет міг передавати їх як dep_values протягом однієї сесії
    # форми, не додаючи колонок до res.partner. Довговічна копія живе на
    # dm.geodata.address (city_moniker/street_moniker), зчитується через
    # _linked_moniker(). Збереження їх додало б колонки res.partner, що валять
    # country pre-check веб-«Upgrade» Odoo 19 (він префетчить усі збережені поля
    # партнера до _auto_init).
    geodata_city_moniker = fields.Char(store=False)
    geodata_street_moniker = fields.Char(store=False)
    # Однорядкове поле пошуку адреси на вкладці «Адресна інформація» (test #9).
    geodata_search = fields.Char(string="Search Address", store=False)

    has_geodata_credential = fields.Boolean(
        compute="_compute_geodata_settings", compute_sudo=True
    )
    geodata_show_manual_hint = fields.Boolean(
        compute="_compute_geodata_settings", compute_sudo=True
    )
    # Рівень валідації (з посилань пов'язаної адреси): які рівні взято з довідника
    # (підказок). Керує індикатором введених вручну даних (червона рамка).
    geodata_city_verified = fields.Boolean(compute="_compute_geodata_verified")
    geodata_street_verified = fields.Boolean(compute="_compute_geodata_verified")
    geodata_zip_verified = fields.Boolean(compute="_compute_geodata_verified")
    geodata_verified_level = fields.Char(
        compute="_compute_geodata_verified", string="Verified up to")

    # Документні/листові адреси: compute на боці власника (а не related), щоб у
    # шаблонах були доступні Odoo-поля власника ({partner_name}/{company_name}/
    # {street2}). Non-stored -> завжди свіже після зміни шаблону в Налаштуваннях.
    geodata_address_full_ua = fields.Char(
        compute="_compute_geodata_documents", string="Document address (UA)")
    geodata_address_full_en = fields.Char(
        compute="_compute_geodata_documents", string="Document address (EN)")
    geodata_address_letter_ua = fields.Char(
        compute="_compute_geodata_documents", string="Envelope address (UA)")
    geodata_address_letter_en = fields.Char(
        compute="_compute_geodata_documents", string="Envelope address (EN)")
    # Перший рядок (повна адреса) на вкладці контакту — за конфігурованим шаблоном.
    geodata_address_display = fields.Char(
        compute="_compute_geodata_documents", string="Address (display)")
    # Дві рендеровані колонки «Деталі адреси» (з конфігурованих шаблонів
    # credential). Non-stored compute -> завжди свіже після зміни шаблону в
    # Налаштуваннях.
    # Html, щоб URL у шаблоні були клікабельними (контент екрануємо самі ->
    # sanitize не потрібен і не зрізає target).
    geodata_details_col1 = fields.Html(
        compute="_compute_geodata_details", sanitize=False,
        string="Address details: column 1")
    geodata_details_col2 = fields.Html(
        compute="_compute_geodata_details", sanitize=False,
        string="Address details: column 2")
    geodata_kato = fields.Char(related="geodata_address_id.kato", readonly=True)
    geodata_koatuu = fields.Char(related="geodata_address_id.koatuu", readonly=True)
    geodata_terr_status = fields.Char(
        related="geodata_address_id.terr_status", readonly=True)
    geodata_address_updated = fields.Datetime(
        related="geodata_address_id.write_date", readonly=True,
        string="Address Updated")

    # Додаткові українські адмін-рівні, які заповнює довідник (не стандартні Odoo).
    area = fields.Char(string="District/Raion")
    hromada = fields.Char(string="Territorial Community")

    # Логічний рівень адреси -> реальне ім'я поля власника. Інтеграційні модулі,
    # чия модель має нестандартні імена (напр. hr.employee `private_*`, res.bank
    # `state`/`country`), перевизначають цю мапу; решта — незалежна від імен полів.
    _geodata_fields = {
        "country_id": "country_id", "state_id": "state_id",
        "city": "city", "street": "street", "street2": "street2", "zip": "zip",
        "area": "area", "hromada": "hromada",
    }

    def _compute_geodata_settings(self):
        credential = self.env["dm.geodata.api.credential"].sudo().get_credential()
        has = bool(credential)
        hint = credential.show_manual_hint if credential else True
        for rec in self:
            rec.has_geodata_credential = has
            rec.geodata_show_manual_hint = hint

    # Курований перелік Odoo-полів контакту, доступних у ВСІХ шаблонах
    # (плейсхолдер -> атрибут на res.partner). Не «будь-яке поле»: лише безпечні
    # загальні поля. На інших моделях-власниках відсутні поля -> порожньо.
    _OWNER_EXTRA_FIELDS = {
        "name": "name",
        "partner_name": "display_name",  # alias (сумісність)
        "company_name": "commercial_company_name",
        "vat": "vat",
        "ref": "ref",
        "function": "function",
        "title": "title",
        "phone": "phone",
        "mobile": "mobile",
        "email": "email",
    }

    def _owner_field_value(self, attr):
        """Безпечне читання поля власника (з правами користувача): відсутнє поле
        або брак доступу -> ''; recordset -> display_name; інше -> str."""
        self.ensure_one()
        if attr not in self._fields:
            return ""
        try:
            value = self[attr]
        except AccessError:
            return ""
        if not value:
            return ""
        if isinstance(value, models.BaseModel):
            return value.display_name or ""
        return str(value)

    def _geodata_owner_extra(self):
        """Курований набір Odoo-полів контакту для плейсхолдерів у шаблонах."""
        self.ensure_one()
        extra = {ph: self._owner_field_value(attr)
                 for ph, attr in self._OWNER_EXTRA_FIELDS.items()}
        street2_field = self._geodata_fields.get("street2", "street2")
        extra["street2"] = self._owner_field_value(street2_field)
        # Індекс власника має пріоритет у шаблонах адрес (документи/конверти/рядок
        # картки): якщо власник увів свій zip — показуємо саме його ({Index_}),
        # навіть коли в довіднику є post_index. Порожній zip -> лишається
        # довідниковий індекс.
        zip_field = self._geodata_fields.get("zip")
        owner_zip = self[zip_field] if zip_field in self._fields else False
        if owner_zip:
            extra["Index_"] = owner_zip
        return extra

    # Поля вкладки — нестора́жні compute із пов'язаної dm.geodata.address, яку
    # apply_address мутує «на місці» (той самий id). OWL дедуплікує незмінений
    # m2o, тож залежності лише від geodata_address_id НЕ перерахувались би при
    # перевиборі міста/вулиці. Додаємо адресні поля власника (через _geodata_fields,
    # з гардом in self._fields, бо на абстрактному міксині їх немає) + write_date,
    # щоб вкладка свіжала на вибір підказки/Enter/blur/збереження.
    @api.depends(lambda self: [
        "geodata_address_id", "geodata_address_id.write_date",
    ] + [self._geodata_fields[k]
         for k in ("street2", "city", "street", "zip", "area", "hromada", "state_id")
         if self._geodata_fields.get(k) in self._fields])
    def _compute_geodata_documents(self):
        credential = self.env["dm.geodata.api.credential"].sudo().get_credential()
        store_en = credential.store_english if credential else False
        for rec in self:
            addr = rec.geodata_address_id.sudo()
            extra = rec._geodata_owner_extra()
            if addr and credential:
                doc = credential.address_format_document
                letter = credential.address_format_letter
                rec.geodata_address_full_ua = addr._render_api_template(doc, "ua", extra)
                rec.geodata_address_letter_ua = addr._render_api_template(letter, "ua", extra)
                rec.geodata_address_full_en = (
                    addr._render_api_template(doc, "en", extra) if store_en else False)
                rec.geodata_address_letter_en = (
                    addr._render_api_template(letter, "en", extra) if store_en else False)
                rec.geodata_address_display = addr._render_api_template(
                    credential.address_format_display, "ua", extra)
            else:
                rec.geodata_address_full_ua = False
                rec.geodata_address_full_en = False
                rec.geodata_address_letter_ua = False
                rec.geodata_address_letter_en = False
                rec.geodata_address_display = False

    # Бари URL у колонках робимо клікабельними. Lookbehind, щоб не чіпати URL
    # усередині href="…"/значень атрибутів; зупиняється на пробілі/`<`.
    _URL_RE = re.compile(r"(?<![\"'=])https?://[^\s<]+")

    @api.model
    def _geodata_html_finalize(self, text):
        """Фіналізація HTML-колонки: вхід — рядок із СИРИМ адмінським HTML
        (літерал шаблону) та вже екранованими значеннями. Тут лише:
        1) обгортаємо бари URL у <a>; 2) прибираємо переноси строго між тегами
        (щоб не ламати таблиці); 3) решту \\n -> <br/>."""
        if not text:
            return False
        parts = []
        last = 0
        for m in self._URL_RE.finditer(text):
            parts.append(text[last:m.start()])  # сирий (HTML + екрановані значення)
            url = m.group(0)
            parts.append(str(Markup(
                '<a href="%s" target="_blank" rel="noreferrer noopener">%s</a>'
            ) % (url, url)))
            last = m.end()
        parts.append(text[last:])
        out = "".join(parts)
        out = re.sub(r">[ \t]*\n[ \t]*<", "><", out)  # переноси між тегами
        out = out.replace("\n", "<br/>")
        return Markup(out)

    # Та сама причина свіжості, що й у _compute_geodata_documents: залежимо від
    # write_date пов'язаної адреси та адресних полів власника, інакше col1/col2 не
    # перераховуються при перевиборі з тим самим dm.geodata.address.
    @api.depends(lambda self: [
        "geodata_address_id", "geodata_address_id.write_date",
    ] + [self._geodata_fields[k]
         for k in ("street2", "city", "street", "zip", "area", "hromada", "state_id")
         if self._geodata_fields.get(k) in self._fields])
    def _compute_geodata_details(self):
        credential = self.env["dm.geodata.api.credential"].sudo().get_credential()
        for rec in self:
            addr = rec.geodata_address_id.sudo()
            extra = rec._geodata_owner_extra()
            if addr and credential:
                rec.geodata_details_col1 = rec._geodata_html_finalize(
                    addr._render_api_template(
                        credential.details_format_col1 or "", "ua", extra,
                        escape_values=True))
                rec.geodata_details_col2 = rec._geodata_html_finalize(
                    addr._render_api_template(
                        credential.details_format_col2 or "", "ua", extra,
                        escape_values=True))
            else:
                rec.geodata_details_col1 = False
                rec.geodata_details_col2 = False

    @api.depends(lambda self: [
        "geodata_address_id", "geodata_address_id.settlement_ref",
        "geodata_address_id.street_ref", "geodata_address_id.house_ref",
        "geodata_address_id.post_index",
    ] + ([self._geodata_fields["street"]]
         # Поле вулиці власника існує лише на конкретних моделях-bridge, а НЕ на
         # абстрактному міксині — інакше резолвинг depends на абстрактній моделі
         # падає й валить усі поля міксина (has_geodata_credential тощо).
         if self._geodata_fields["street"] in self._fields else [])
      + ([self._geodata_fields["zip"]]
         if self._geodata_fields.get("zip") in self._fields else []))
    def _compute_geodata_verified(self):
        # Тумблера «старі назви» більше немає -> валідовану вулицю для порівняння
        # ручних правок будуємо без історичних назв.
        show_old = False
        for rec in self:
            addr = rec.geodata_address_id
            city_v = bool(addr and addr.settlement_ref)
            street_v = bool(addr and addr.street_ref)
            # Жива перевірка вулиці: ручна зміна НАЗВИ вулиці (не лише номера
            # будинку) знімає підтвердження ОДРАЗУ (без збереження картки) — тією
            # самою логікою, що й _geodata_sync_on_manual_change на write, тож
            # підсвічування «введено вручну» збігається до і після збереження.
            # Порожнє поле -> лишаємо за street_ref (узгоджено з застосуванням
            # підказки, де значення ще не матеріалізоване в полі власника).
            if street_v:
                owner_street = rec[rec._geodata_fields["street"]]
                if owner_street:
                    geo = addr.sudo()
                    # Валідована вулиця напряму (без to_address_values/get_credential).
                    street = geo._street_display("ua", show_old)
                    house = geo._house_part()
                    validated = ("%s, %s" % (street, house) if street and house
                                 else (street or house))
                    if (rec._norm(owner_street) != rec._norm(validated)
                            and not rec._is_house_only_change(geo, owner_street)):
                        street_v = False
            house_v = bool(addr and addr.house_ref)
            # Індекс: підтверджений, якщо власників zip збігається з довідниковим
            # post_index. Ручна правка (або відсутність у довіднику) -> не
            # підтверджено -> помітка «введено вручну».
            zip_field = rec._geodata_fields.get("zip")
            owner_zip = rec[zip_field] if zip_field in rec._fields else False
            rec.geodata_zip_verified = bool(
                addr and addr.post_index and owner_zip
                and rec._norm(owner_zip) == rec._norm(addr.post_index))
            rec.geodata_city_verified = city_v
            rec.geodata_street_verified = street_v
            if house_v:
                rec.geodata_verified_level = "house"
            elif street_v:
                rec.geodata_verified_level = "street"
            elif city_v:
                rec.geodata_verified_level = "settlement"
            else:
                rec.geodata_verified_level = "none"

    # ------------------------------------------------------------------
    # Строге володіння 1:1: dm.geodata.address належить рівно одному власнику й
    # ніколи не спільна. Коли власник скидає зв'язок (reset / ручна зміна
    # населеного пункту) або видаляється, його приватний рядок стає сиротою й
    # видаляється. Централізовано тут на write/unlink, щоб покрити кожен шлях
    # відв'язування.
    # ------------------------------------------------------------------
    def write(self, vals):
        # Тримаємо пов'язану dm.geodata.address лише підтвердженою: ручна правка
        # поля адресного блоку (що більше не збігається з валідованими даними)
        # відв'язує/понижує зв'язок. Пропускається, поки віджет застосовує підказку
        # (geodata_applying).
        if not self.env.context.get("geodata_applying"):
            addr_fields = [self._geodata_fields[lvl] for lvl in self._GEO_ADDRESS_LEVELS]
            if any(fld in vals for fld in addr_fields):
                for rec in self:
                    if rec.geodata_address_id:
                        rec._geodata_sync_on_manual_change(vals)
        old_links = self.env["dm.geodata.address"]
        if "geodata_address_id" in vals:
            old_links = self.mapped("geodata_address_id")
        res = super().write(vals)
        if old_links:
            self._geodata_gc_orphans(old_links)
        return res

    def unlink(self):
        orphans = self.mapped("geodata_address_id")
        res = super().unlink()
        self._geodata_gc_orphans(orphans)
        return res

    def _geodata_gc_orphans(self, addresses):
        """Delete the given dm.geodata.address rows that no longer have any owner.

        Safe under the strict 1:1 model: a row referenced by no owner is dead
        data. Only this owner model is checked for references (single owner
        today); a row still pointed at by some record is kept."""
        model = self.with_context(active_test=False)
        for addr in addresses:
            if not addr or not addr.exists():
                continue
            if model.search_count([("geodata_address_id", "=", addr.id)]) == 0:
                addr.sudo().unlink()

    # ------------------------------------------------------------------
    # Синхронізація адреси на боці власника (загальна, керується `_geodata_fields`).
    # Інтеграційні модулі оголошують тонкі @api.onchange-обгортки, що викликають
    # `_geodata_onchange(level)` для своїх реальних імен полів; усе нижче —
    # незалежне від імен полів через мапу.
    # ------------------------------------------------------------------
    # Залежні рівні, що очищуються при ручній зміні даного рівня. area/hromada
    # походять від населеного пункту, тож зміна міста очищує і їх.
    _GEO_CLEAR_BELOW = {
        "state_id": ("area", "hromada", "city", "street", "street2", "zip"),
        "area": ("hromada", "city", "street", "street2", "zip"),
        "hromada": ("city", "street", "street2", "zip"),
        "city": ("area", "hromada", "street", "street2", "zip"),
        "street": ("street2", "zip"),
    }
    # Рівень населеного пункту й вище: ручне розходження відв'язує зв'язок.
    _GEO_DETACH_LEVELS = ("state_id", "area", "hromada", "city")
    # Рівні, що порівнюються з валідованою адресою при збереженні (write).
    _GEO_ADDRESS_LEVELS = ("state_id", "area", "hromada", "city", "street", "zip")

    def _geodata_is_ua(self):
        country = self[self._geodata_fields["country_id"]]
        return bool(country and country.code == "UA")

    def _geodata_clear_block(self, level):
        for lvl in self._GEO_CLEAR_BELOW.get(level, ()):
            self[self._geodata_fields[lvl]] = False

    def _geodata_detach(self):
        """Detach the validated Geodata link and its monikers."""
        self.geodata_address_id = False
        self.geodata_city_moniker = False
        self.geodata_street_moniker = False

    def _norm(self, value):
        # Прибираємо будь-яке «(стара назва)» у дужках, щоб порівняння не залежали
        # від суфікса історичної назви (show_old_names) — його перемикання не має
        # виглядати як ручна правка.
        if isinstance(value, str):
            return self._strip_old_paren(value) or False
        return value

    def _geodata_live_sync(self, level):
        """Live (onchange) detach: if a settlement-level field no longer matches
        the linked address, drop the link so the address block clears in-form."""
        if not self.geodata_address_id or level not in self._GEO_DETACH_LEVELS:
            return
        expected = self.geodata_address_id.sudo().to_address_values()
        field = self._geodata_fields[level]
        if level == "state_id":
            current = self[field].id if self[field] else False
            if (current or False) != (expected.get("state_id") or False):
                self._geodata_detach()
        elif self._norm(self[field]) != self._norm(expected.get(level)):
            self._geodata_detach()

    def _geodata_onchange(self, level):
        """Generic onchange body: live-detach (settlement+) and clear-down."""
        if self.geodata_autocomplete_active or not self._geodata_is_ua():
            return
        # Ручне редагування адресного блоку робить однорядковий «Пошук адреси»
        # неактуальним — очищуємо його. Гард вище гарантує, що під час
        # застосування підказки (geodata_autocomplete_active) значення не чіпаємо,
        # тож прогресивний пошук місто->вулиця->будинок працює як раніше.
        self.geodata_search = False
        if level in self._GEO_DETACH_LEVELS:
            self._geodata_live_sync(level)
        self._geodata_clear_block(level)

    def _geodata_sync_on_manual_change(self, vals):
        """Persisted counterpart of the onchange: compare incoming block values
        (real field names in `vals`) with the validated values derived from the
        linked dm.geodata.address; settlement+ divergence -> detach, street -> downgrade."""
        self.ensure_one()
        geo = self.geodata_address_id.sudo()
        expected = geo.to_address_values()
        fmap = self._geodata_fields
        new = {}
        for level in self._GEO_ADDRESS_LEVELS:
            real = fmap[level]
            if real in vals:
                new[level] = vals[real]
            elif level == "state_id":
                new[level] = self[real].id if self[real] else False
            else:
                new[level] = self[real]

        changed = {
            "city": fmap["city"] in vals
            and self._norm(new["city"]) != self._norm(expected.get("city")),
            "area": fmap["area"] in vals
            and self._norm(new["area"]) != self._norm(expected.get("area")),
            "hromada": fmap["hromada"] in vals
            and self._norm(new["hromada"]) != self._norm(expected.get("hromada")),
            "state_id": fmap["state_id"] in vals
            and (new["state_id"] or False) != (expected.get("state_id") or False),
        }
        if any(changed.values()):
            self._geodata_detach()
            for level in ("state_id", "area", "hromada", "city"):
                if changed[level]:
                    for lvl in self._GEO_CLEAR_BELOW[level]:
                        real = fmap[lvl]
                        if real not in vals:
                            vals[real] = False
                    break
            return

        street_field = fmap["street"]
        if street_field in vals and self._norm(vals[street_field]) != self._norm(expected.get("street")):
            if self._is_house_only_change(geo, vals[street_field]):
                geo.write({
                    "house_ref": False, "house_num": False, "house_num_add": False,
                    "house_num_add_en": False, "house_string": False,
                    "latitude": 0.0, "longitude": 0.0,
                })
            else:
                # Очищуємо й EN-відповідники (street_en/str_type_en/
                # house_num_add_en); інакше EN документна/листова адреса збереже
                # стару транслітеровану вулицю, тоді як UA її вже прибрала
                # (_field_lang для EN відкочується до *_en).
                geo.write({
                    "street_ref": False, "house_ref": False, "street": False,
                    "str_type": False, "street_string": False, "house_num": False,
                    "house_num_add": False, "house_string": False,
                    "street_en": False, "str_type_en": False,
                    "house_num_add_en": False,
                    "latitude": 0.0, "longitude": 0.0,
                })

    @staticmethod
    def _is_house_only_change(geo, new_street):
        """True when the new street value still contains the validated street
        name (i.e. only the house number/letter changed)."""
        if not geo.street:
            return False
        return geo.street.lower() in (new_street or "").lower()

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------
    def _geodata_company_id(self):
        """Company to scope this owner's private dm.geodata.address to.

        Mirrors the owner so the address is visible exactly where the owner is:
        a multi-company-shared owner (`company_id` empty) -> a shared (global)
        address. Models without a `company_id` field (e.g. res.bank) keep their
        address global; res.company overrides this to its own id."""
        self.ensure_one()
        if "company_id" in self._fields:
            return self.company_id.id
        return False

    @api.model
    def _geodata_credential(self):
        return self.env["dm.geodata.api.credential"].sudo().get_credential()

    def _geodata_country_ok(self, dep):
        """Search only when the selected country is Ukraine (test #1).

        Robust across owner models: accept the `country_code` string when the
        form carries it, otherwise fall back to `country_id` pointing at Ukraine.
        The address block always loads `country_id`, while a related
        `country_code` field is not reliably loaded into the form record on some
        models (e.g. crm.lead / res.company)."""
        dep = dep or {}
        if dep.get("country_code") == "UA":
            return True
        ukraine = self.env.ref("base.ua", raise_if_not_found=False)
        return bool(ukraine and dep.get("country_id") == ukraine.id)

    # ------------------------------------------------------------------
    # Точки входу автопідказки (викликаються з OWL-віджета через RPC).
    # Доступні будь-якому внутрішньому користувачу; привілейований доступ через
    # sudo (AUDIT #1/#2).
    # ------------------------------------------------------------------
    @api.model
    def geodata_autocomplete_cities(self, query, dep_values=None):
        if not self._geodata_country_ok(dep_values):
            return []
        credential = self._geodata_credential()
        if not credential:
            return []
        query = credential._normalize_query(self._strip_old_paren(query))
        if len(query) < (credential.min_chars or 3):
            return []
        region = self._region_from_state((dep_values or {}).get("state_id"))
        # Без кешу: кожен реальний пошук має йти в API (ціль — дохід за виклик).
        results = credential.api_cities(query, lang="uk_UA", region=region)
        return [s for s in (self._format_city_suggestion(d) for d in results
                            if isinstance(d, dict)) if s]

    @api.model
    def geodata_autocomplete_streets(self, query, dep_values=None):
        """Street suggestions, and house suggestions once a street is picked.

        Routing (test #3/#4): if a street is already selected
        (``geodata_street_moniker`` present) and the query ends with a house
        token after the street name, query Houses; otherwise query Streets.
        """
        if not self._geodata_country_ok(dep_values):
            return []
        credential = self._geodata_credential()
        if not credential:
            return []
        dep = dep_values or {}
        # Прибираємо «(стару назву)», яку може нести поле, щоб розбір вулиці/будинку
        # бачив чисту чинну назву (аналогічно до прибирання типу вулиці).
        raw = self._strip_old_paren(query)
        geo_addr = self._dep_geo_address(dep)
        # Монікер беремо передусім зі ЗБЕРЕЖЕНОГО запису, поки він свіжий (живе
        # ~15 хв) — БЕЗ зайвого переотримання через API Cities. Транзитивне поле
        # власника (dep) — лише запасний хінт (губиться на round-trip'ах). Ре-резолв
        # (API Cities) лише коли монікера немає або він застарів.
        city_moniker = ""
        if geo_addr.exists() and self._moniker_fresh(geo_addr.city_moniker_ts):
            city_moniker = geo_addr.city_moniker or ""
        if not city_moniker:
            city_moniker = dep.get("geodata_city_moniker") or ""
        if not city_moniker and geo_addr.exists():
            city_moniker = self._refresh_city_moniker(credential, geo_addr)
        if not city_moniker:
            return []
        street_moniker = ""
        if geo_addr.exists() and self._moniker_fresh(geo_addr.street_moniker_ts):
            street_moniker = geo_addr.street_moniker or ""
        if not street_moniker:
            street_moniker = dep.get("geodata_street_moniker") or ""
        # Чиста мітка ВЖЕ ВИБРАНОЇ вулиці (без номера будинку) — береться з
        # пов'язаної dm.geodata.address, а НЕ із сирого вмісту поля (#4).
        clean_label = self._build_street_label(geo_addr)

        # Режим будинку: вулицю вибрано, і після назви вулиці йде номер.
        if street_moniker and clean_label and raw.lower().startswith(clean_label.lower()):
            remainder = raw[len(clean_label):].strip()
            match = re.match(r"^[,\s]*(\d[\w\-/]*)", remainder) or _HOUSE_TAIL_RE.search(raw)
            if match:
                house_q = match.group(1)
                results = credential.api_houses(house_q, street_moniker, lang="uk_UA")
                if isinstance(results, dict):  # moniker протермінувався -> оновити раз
                    street_moniker = self._refresh_street_moniker(
                        credential, geo_addr, city_moniker)
                    results = credential.api_houses(
                        house_q, street_moniker, lang="uk_UA") if street_moniker else []
                if isinstance(results, dict):
                    return []
                return [s for s in (self._format_house_suggestion(d, geo_addr.street_string or "")
                                    for d in results) if s]

        # Режим вулиці.
        clean = credential._normalize_query(self._strip_street_type(raw))
        if len(clean) < 2:
            return []
        results = credential.api_streets(clean, city_moniker, lang="uk_UA")
        if isinstance(results, dict):  # moniker протермінувався -> оновити й повторити
            city_moniker = self._refresh_city_moniker(credential, geo_addr)
            results = credential.api_streets(
                clean, city_moniker, lang="uk_UA") if city_moniker else []
        if isinstance(results, dict) or not isinstance(results, list):
            return []
        return [s for s in (self._format_street_suggestion(d) for d in results) if s]

    @staticmethod
    def _moniker_fresh(ts):
        """True while a stored moniker is still within its ~15-min lifetime."""
        return bool(ts) and (fields.Datetime.now() - ts) < _MONIKER_TTL

    def _refresh_city_moniker(self, credential, geo_addr):
        """Re-resolve & persist the city moniker on the linked address."""
        if not geo_addr or not geo_addr.exists():
            return ""
        moniker = credential._resolve_city_moniker(geo_addr)
        if moniker:
            geo_addr.sudo().write({
                "city_moniker": moniker, "city_moniker_ts": fields.Datetime.now()})
        return moniker

    def _refresh_street_moniker(self, credential, geo_addr, city_moniker):
        if not geo_addr or not geo_addr.exists():
            return ""
        moniker = credential._resolve_street_moniker(geo_addr, city_moniker)
        if moniker:
            geo_addr.sudo().write({
                "street_moniker": moniker, "street_moniker_ts": fields.Datetime.now()})
        return moniker

    @api.model
    def geodata_autocomplete_full_address(self, query, dep_values=None):
        """One-line full-address search via api/Address (test #9)."""
        if not self._geodata_country_ok(dep_values):
            return []
        credential = self._geodata_credential()
        if not credential:
            return []
        query = credential._normalize_query(query)
        if len(query) < (credential.min_chars or 3):
            return []
        results = credential.api_address(query, lang="uk_UA")
        return [s for s in (self._format_full_address_suggestion(d) for d in results
                            if isinstance(d, dict)) if s]

    def _linked_moniker(self, kind):
        """Fallback: read moniker from the linked dm.geodata.address."""
        if len(self) != 1 or not self.geodata_address_id:
            return ""
        addr = self.geodata_address_id.sudo()
        return (addr.city_moniker if kind == "city" else addr.street_moniker) or ""

    def _region_from_state(self, state_id):
        """Resolve the sRegion filter from the selected state (#3)."""
        if not state_id:
            return ""
        state = self.env["res.country.state"].sudo().browse(int(state_id))
        if not state.exists():
            return ""
        return self.env["dm.geodata.address"]._normalize_region_name(state.name)

    def _dep_geo_address(self, dep):
        """Browse the linked dm.geodata.address from dep_values (or self)."""
        addr_id = dep.get("geodata_address_id")
        if addr_id:
            addr = self.env["dm.geodata.address"].sudo().browse(int(addr_id))
            return addr if addr.exists() else self.env["dm.geodata.address"]
        if len(self) == 1 and self.geodata_address_id:
            return self.geodata_address_id.sudo()
        return self.env["dm.geodata.address"]

    @staticmethod
    def _build_street_label(geo_addr):
        """Clean street label '<str_type> <street>' (no house number)."""
        if not geo_addr:
            return ""
        street = geo_addr.street or ""
        if not street:
            return ""
        str_type = geo_addr.str_type or ""
        return ("%s %s" % (str_type, street)).strip() if str_type else street

    _STREET_TYPE_PREFIXES = (
        "вул.", "вулиця", "просп.", "проспект", "пров.", "провулок",
        "бул.", "бульвар", "б-р", "пл.", "площа", "наб.", "набережна",
        "пр.", "пр-т", "шосе", "алея", "узвіз", "тупик",
    )

    @api.model
    def _strip_street_type(self, query):
        text = (query or "").strip()
        low = text.lower()
        for prefix in self._STREET_TYPE_PREFIXES:
            if low.startswith(prefix + " "):
                return text[len(prefix):].strip()
        return text

    @staticmethod
    def _strip_old_paren(text):
        """Drop any "(old name)" in parentheses so parsing/comparison sees the
        clean current value (the address fields may carry "Name (Old)" when the
        credential's `show_old_names` is on). Transparent, like type-stripping."""
        return re.sub(r"\s*\([^)]*\)", "", text or "").strip()

    # ------------------------------------------------------------------
    # Форматувальники підказок — мітки беруться зі спеціальних полів *String,
    # які API віддає саме для випадних списків (test #5/#6/#7).
    # ------------------------------------------------------------------
    @staticmethod
    def _format_city_suggestion(data):
        if data.get("Id") and not data.get("SettlementId"):
            data["SettlementId"] = data["Id"]
        label = data.get("CityString")
        if not label:
            return None
        return {"label": label, "value": label, "data": data}

    @staticmethod
    def _format_street_suggestion(data):
        if not isinstance(data, dict):
            return None
        label = data.get("StreetString")
        if not label:
            return None
        return {"label": label, "value": label, "data": data}

    @staticmethod
    def _format_house_suggestion(data, street_string=""):
        # Label/value = StreetString + HouseString (обидва — спеціальні поля API).
        # StreetString береться як є (dm.geodata.address.street_string): його формує
        # API, і воно може вже містити стару назву в дужках незалежно від
        # налаштування show_old_names — тож тут воно НЕ прибирається.
        if not isinstance(data, dict):
            return None
        house = data.get("HouseString")
        if not house:
            return None
        label = "%s, %s" % (street_string, house) if street_string else house
        return {"label": label, "value": label, "data": data}

    @staticmethod
    def _format_full_address_suggestion(data):
        label = data.get("AddressString")
        if not label:
            return None
        return {"label": label, "value": label, "data": data}

    # ------------------------------------------------------------------
    # Застосувати вибрану підказку (sudo-сервіс — AUDIT #1/#5).
    # Зливає в наявну dm.geodata.address партнера, щоб увесь ланцюг
    # місто->вулиця->будинок будував ОДИН запис (test #8).
    # ------------------------------------------------------------------
    @api.model
    def apply_address(self, record_id, api_data, current_address_id=False):
        if not api_data:
            return {}
        credential = self._geodata_credential()
        Geo = self.env["dm.geodata.address"].sudo()

        geo_address = Geo.browse(int(current_address_id)) if current_address_id else Geo
        if (not geo_address or not geo_address.exists()) and record_id:
            rec = self.browse(int(record_id))
            if rec.exists() and rec.geodata_address_id:
                geo_address = rec.geodata_address_id.sudo()

        if geo_address and geo_address.exists():
            geo_address.update_from_api(api_data)
        else:
            # Ще немає пов'язаної адреси -> створюємо НОВИЙ приватний рядок (без
            # дедуплікації/повторного використання): модель строго 1:1 із власником.
            geo_address = Geo.create_from_api(api_data)

        # Прив'язуємо приватну адресу до компанії власника, щоб вона була видима
        # саме там, де власник (False = спільний власник -> спільна адреса).
        owner = self.browse(int(record_id)) if record_id else self.browse()
        company_id = (owner._geodata_company_id() if owner.exists()
                      else self.env.company.id)
        if geo_address.company_id.id != company_id:
            geo_address.company_id = company_id

        if credential:
            geo_address.fetch_en_translit(credential)

        values = self._geodata_owner_values(geo_address)
        values["geodata_address_id"] = {
            "id": geo_address.id,
            "display_name": geo_address.display_name or geo_address.address_string or "",
        }
        values["geodata_city_moniker"] = geo_address.city_moniker or False
        values["geodata_street_moniker"] = geo_address.street_moniker or False
        return values

    @api.model
    def _geodata_owner_values(self, geo_address):
        """Map dm.geodata.address -> owner address fields, remapping the standard
        keys (street/city/zip/state_id/area/hromada/country_id) to the real owner
        field names via `_geodata_fields`. Models with non-standard names work
        by just overriding that map; lat/long and other keys pass through."""
        fmap = self._geodata_fields
        return {fmap.get(key, key): value
                for key, value in geo_address.to_address_values().items()}

    # ------------------------------------------------------------------
    # Дії
    # ------------------------------------------------------------------
    def action_view_geodata_address(self):
        """Open the detailed dm.geodata.address form (test #10)."""
        self.ensure_one()
        if not self.geodata_address_id:
            return False
        return {
            "type": "ir.actions.act_window",
            "name": _("Full Address"),
            "res_model": "dm.geodata.address",
            "res_id": self.geodata_address_id.id,
            "view_mode": "form",
            "target": "current",
        }

    def action_geodata_reset(self):
        """Explicitly detach the validated Geodata address (AUDIT #16)."""
        for rec in self:
            rec.geodata_address_id = False
            rec.geodata_city_moniker = False
            rec.geodata_street_moniker = False
        return True
