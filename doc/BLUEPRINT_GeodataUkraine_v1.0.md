# 📄 BLUEPRINT — Geodata Ukraine Address Directory (Odoo 19 CE) · v1.0

> Документ-основа для розробки **нового модуля з нуля** на базі forensic-аудиту попередньої версії
> (`doc/AUDIT.md`, 17 знахідок). Ціль — Odoo **19 Community Edition**, self-hosted Linux, PostgreSQL,
> Python 3.10+. Усі дефекти попередньої версії усунені архітектурно.

**Зафіксовані рішення замовника:**
1. Шарова, де-дубльована структура; `dm_geodata_online` — порожній meta-bundle. **БЕЗ wizard.**
2. **Self-contained** — без зовнішніх `kw_*`/`generic_mixin` (власний API-клієнт + власний OWL-віджет).
3. Мови адрес: **UA + EN** (RU прибрано).
4. API-виконання: **синхронно + debounce/dedup/cache**; транслітерація EN лише при `on_select`.

---

## 1. РЕЗЮМЕ (Executive Summary)

**Мета.** Інтеграція з Geodata.online API для автодоповнення, нормалізації та зберігання українських
адрес із прив'язкою до `res.partner`, `crm.lead`, `hr.employee`, `lunch.supplier`, `res.company`,
плюс провайдер геокодування для `base_geolocalize`.

**Основні компоненти.**
- `dm_geodata_connector` — ядро: модель-сховище `dm.geodata.address`, абстрактний `dm.geodata.address.mixin`,
  власний API-клієнт і креденшали, override `base.geocoder`, власний OWL-віджет `geodata_autocomplete`,
  **health-моніторинг** креденшалів (cron + кнопка).
- `dm_geodata_contact` — інтеграція з `res.partner` (inline-автодоповнення, **без wizard**).
- `dm_geodata_crm` (`crm.lead`), `dm_geodata_company` (`res.company`), `dm_geodata_hr`
  (`hr.employee`, приватна адреса → override `_geodata_fields`), `dm_geodata_bank`
  (`res.bank`, нестандартні m2o `state`/`country` → override) — тонкі auto_install-bridge
  (лише модель-glue + views). **Зроблено.**
- `dm_geodata_lunch` (`lunch.supplier`) — адреса на `related`-полях до `partner_id`
  (як `res.company`), тож власна форма постачальника без власного bridge мала б
  поля без автопідказки. Override `_geodata_fields` лише `zip -> zip_code`, додає
  related `country_code`. Auto_install лише з модулем `lunch`.
- `dm_geodata_online` — порожній meta-bundle (App Store).
- `dm_test_geodata_connector` — тести + mock API (окремий, не для production).

**Health-моніторинг (проактивний контроль).** Хибна конфігурація «німа» (немає
активного `dm.geodata.api.credential` → автопідказка просто не працює, HTTP-виклик
навіть не робиться). Тому креденшал перевіряється завчасно: щоденний cron
**Geodata: health check** + кнопка **Check Now** перевіряють доступність сервера,
авторизацію, **баланс** (`balance_alert_threshold`) і наявність активного
креденшала. Реакція — запис у лог (`WARNING`/`ERROR`) **і** живий попап
менеджерам (`group_geodata_manager`, `bus.bus`, throttled). Стан видно у блоці
**Status** / сторінці **Monitoring** (`health_status`, `last_balance`,
`health_last_check`, `health_message`). Доповнює реактивний шлях HTTP-402.

**Топ-критичні зауваження аудиту → рішення (повна матриця — Додаток 7.1).**
| # | Проблема (стара версія) | Рішення в новому модулі |
|---|---|---|
| #1/#2 | `dm.geodata.address` write=0 для user → autocomplete не зберігається; модель недоступна звичайним користувачам | Записи довідника через **service-шар `sudo()`**; autocomplete доступний `base.group_user`; група лише для адміністрування |
| #3 | Виклик **неіснуючих** `kw_autocomplete_areas/hromadas` у 5 модулях | area/hromada — **readonly auto-filled** з вибору адреси (методи не потрібні) |
| #4 | Немає `ir.rule` → витік даних між компаніями | Company-isolation `ir.rule` на `dm.geodata.address` / `dm.geodata.api.credential` / `dm.geodata.request.log`; адреса дзеркалить компанію власника; лог і health-алерти — per-company |
| #5 | Синхронні HTTP у ORM `create` + множник у майстрі | Жодного HTTP у `create`; ingestion/транслітерація лише в явному `on_select`; wizard відсутній |
| #11/#15 | Токен відкритим текстом у БД і в логах headers | Токен у `ir.config_parameter` (sudo); власний logger **маскує** `Authorization` |
| #16 | «Мовчазне очищення» документних адрес при ручній правці | Зберігати документні поля / попереджати перед скиданням |
| #17 | Запити по пробілу, дубль «Київ»/«Київ » | debounce 300мс + dedup + `strip` **до** перевірки довжини |

**Production go/no-go:** новий дизайн знімає всі блокери ст_arої версії → **Conditional Go** після реалізації за цим blueprint + 95% тестового покриття.

---

## 2. АРХІТЕКТУРА МОДУЛЯ

### 2.1 Дерево модулів і залежності
```
                         dm_geodata_online  (meta: ТІЛЬКИ depends, без коду)
                          │  depends: усі нижче
   ┌───────────┬──────────┼───────────┬───────────┐
   ▼           ▼          ▼            ▼           ▼
geodata_   geodata_   geodata_     geodata_    geodata_
company    crm        hr           lunch       contact
(res.      (crm.lead) (hr.employee)(lunch.     (res.partner)
 company)                           supplier)
   └───────────┴──────────┴───────────┴───────────┘
                          │ depends
                          ▼
                  dm_geodata_connector  (CORE)
                   ├─ dm.geodata.address            (сховище адрес)
                   ├─ dm.geodata.address.mixin      (Abstract, спільна логіка)
                   ├─ dm.geodata.api.credential     (власна, без kw_*)
                   ├─ geodata.api.client         (Transient/AbstractModel: requests)
                   ├─ dm.geodata.request.log        (опц., маскований лог)
                   ├─ base.geocoder              (override провайдера)
                   └─ static/src OWL widget      (geodata_autocomplete)
                          │ depends
                          ▼
              base, base_geolocalize, web   (тільки штатні Odoo 19)
```
**Жодних `kw_api_connector`, `kw_widget_autocomplete`, `kw_http_request_log`, `kw_mixin`, `generic_mixin`.**

### 2.2 ER-діаграма (зв'язки моделей)
```
res.partner ─┐
crm.lead    ─┤ M2o geodata_address_id (ondelete=set null)
hr.employee ─┼──────────────► dm.geodata.address ──── M2o state_id ──► res.country.state
lunch.supplier (via partner) │                  (region → state, лише явний синк)
res.company   (via partner) ─┘
                                   ▲
                  get_credential() │ (sudo, company-aware)
                              dm.geodata.api.credential ── M2o company_id ──► res.company
                                   │ 1—n (опц.)
                              dm.geodata.request.log (маскований, M2o company_id)
```
> **Мультикомпанія.** `dm.geodata.address.company_id` дзеркалить компанію власника
> (`_geodata_company_id`: спільний власник → спільна адреса; `res.company` → сама
> себе). `dm.geodata.request.log` має `company_id` (компанія креденшала або компанія
> викликача) і `ir.rule` (global + `company_ids`). Health-алерти — **per-company**
> (менеджерам відповідної компанії; глобальний креденшал → усім).

### 2.3 Діаграма взаємодії (потік даних)
```
[Browser OWL geodata_autocomplete]
   │ debounce 300ms, min_chars 3, skip-on-space/unchanged
   ▼ ORM call (call_kw)
[dm.geodata.address.mixin: autocomplete_cities/streets]  ← доступно base.group_user
   │ normalize+strip+dedup+cache (server)
   ▼ sudo service
[dm.geodata.api.credential._api_request] → requests (timeout, masked log)
   ▼ on_select
[apply_address (sudo)] → upsert dm.geodata.address (dedup) + fetch EN translit (1×, guarded)
   ▼
[partner/lead/employee/... write] (з context skip-clear)
```

---

## 3. ДЕТАЛЬНА СПЕЦИФІКАЦІЯ МОДЕЛЕЙ

### 3.1 `dm.geodata.address` (Model) — сховище нормалізованих адрес
**Призначення:** канонічне зберігання адреси з кодами (KATOTTG/KOATUU), координатами, UA+EN-полями.

**Поля (групи; лише UA + EN — без `*_ru`):**
- Ідентифікатори: `geodata_id` (Integer, index, **частина unique-ключа**), `settlement_ref` (Integer, index), `street_ref` (Integer, index), `house_ref` (Integer, index), `city_moniker` (Char, copy=False), `street_moniker` (Char, copy=False).
- Адміністративні UA: `region`, `area`, `hromada`, `city`, `settlement_type`, `city_district`, `street`, `str_type`, `house_num`, `house_num_add`, `apartment_type`, `apartment`, `addition_address` (Char).
- EN-транслітерація (повний набір `_en`): `region_en`, `area_en`, `hromada_en`, `city_en`, `settlement_type_en`, `city_district_en`, `street_en`, `str_type_en`, **`house_num_add_en`**, `apartment_type_en` (+ old-варіанти `_en`).
- Старі назви: `region_old`, `area_old`, `city_old`, `street_old`, `str_type_old` (+ `_en`).
- Коди/гео: `post_index`, `koatuu`, `kato`, `phone_code` (Char); `latitude`, `longitude`, `latitude_settlement`, `longitude_settlement` (Float digits=(10,7)); `is_regional_center`, `is_district_center` (Boolean); `terr_status` (Char).
- **`api_payload`** (`fields.Json`, copy=False) — сирий відповідь API **вербатим** per-lang (`"ua"`/`"en"`, злитий по ланцюгу місто→вулиця→будинок). Гарантує «store everything»: жодне поле (навіть нове/недокументоване) не втрачається.
- Computed **store=True**: `name`, `address_string`, `address_ua_postal`, `address_ua_short`, `address_western`, `address_full_ua`, `address_full_en`, `address_letter_ua`, `address_letter_en`.

> **Рішення:** прибрати `*_ru` та `*_string_*`-поля, що в старій версії були write-only (С.поле CityString-аналізу). Канонічний дисплей міста будується з `settlement_type+city(+old)`.

**Методи:**
- `_compute_name`, `_compute_address_string`, `_compute_address_formats`, `_compute_full_addresses` — форматери; **credential передається параметром** у внутрішні форматери (без `get_credential()` у циклі — #7).
- `format_address_*` / `_format_full_address(lang, credential)` / `_format_letter_address(lang, credential)` — UA/EN. Документні/листові адреси **ЗАВЖДИ зі старим** (не гейтяться на `show_old_names`); шаблон → `_render_template(template, lang)`, fallback → `_collect_parts(lang, show_old=True)`.
- **Старі назви (історичні):** для рівнів із типом (місто/вулиця) — `_typed_display(name, type_cur, name_old, type_old)` (+ `_city_display`/`_street_display`): «old» охоплює **і назву, і тип**, а **розташування дужки залежить від того, що змінилось**: стара **назва** → у кінці (`вул. Стуса Василя (вул. Механізаторська)`); лише **тип** → одразу після поточного типу, перед назвою (`селище (смт) Іваничі`). **Населений пункт — окреме правило (`_city_old_display`):** `city_old` показується лише як **справжнє перейменування** — коли `suburb_old` порожнє (`SuburbOld == null`) і `city_old != city`; якщо `suburb_old` заповнене, `CityOld` — старе **адмінпідпорядкування** (не назва) і **придушується скрізь**.
- **Шаблони форматів (документ/лист):** шаблон — впорядкований список плейсхолдерів; непорожні сегменти — **через кому** (`_render_template`). Базові `{region}/{area}/{hromada}/{city}/{street}` → лише **поточне**; базовий, за яким одразу йде його `{X_old}`, **об'єднується** в один сегмент `поточне (старе)` (для city/street — через повний `_city_display`/`_street_display(show_old=True)`, тож зі старим типом). Самотній `{*_old}` → гола стара назва (мово-залежна, EN-транслітерація). Кожен плейсхолдер — лише раз (`_check_address_format`). Обидва поля мають `default = _DEFAULT_ADDRESS_FORMAT`. `_OLD_PAIRS`/`_join_old` — допоміжні. EN старих назв вимагає колонок `*_old_en` (`region/area/hromada/settlement_type/city/str_type/street`), що захоплюються `_EN_API_KEYS`/`fetch_en_translit`.
- **Адресний блок партнера:** `to_address_values` застосовує старі назви/типи до city/street/area/hromada **лише коли** `_show_old_names()` (через `_with_old`/`_city_display`/`_street_display`). `_strip_old_paren(text)` (regex `\s*\([^)]*\)`) прозоро **відкидає `(...)`** у autocomplete (cities/streets) і у верифікації `res_partner._norm` — як відкидається тип вулиці, тож пошук/порівняння бачать чисту назву.
- `_api_data_to_vals(api_data)` / `apply_api_values(self, api_data)` — мапінг (без HTTP).
- `create_from_api(api_data)` (@api.model, **sudo service**) — **завжди створює новий рядок** (без дедуплікації/перевикористання); **без HTTP усередині `create`** (#5). Модель строго 1:1 із власником.
- `fetch_en_translit(credential)` — викликається **лише** з `on_select`-сервісу, з `geodata_skip_translit` guard. Захоплює **ВСІ** `_en`-поля з EN-відповіді через мапу `_EN_API_KEYS` (а не 7 hardcoded) — включно з `house_num_add_en` (суфікс будинку), `city_district_en`, old-полями. Запис у `api_payload["en"]` (`_merge_raw`).
- `_house_part(lang="ua")` — **мово-залежний** суфікс будинку: для `en` бере `house_num_add_en` (fallback на UA). Раніше завжди підставлявся кириличний суфікс (`14Д` в EN) — виправлено.
- `_merge_raw(api_data, lang)` — зливає сирий dict у `api_payload[lang]` без втрат; викликається з `create_from_api`/`update_from_api` (`"ua"`) та `fetch_en_translit` (`"en"`).

**Constraints:**
- **Без** `UNIQUE(geodata_id)` і **без дедуплікації**: дві сутності з однаковою адресою мають кожна свій рядок (1:1). `geodata_id` — звичайний індекс.
- `@api.constrains` для координат (валідні діапазони) і формату плейсхолдерів (у credential).

**Спадкування:** немає (нова базова модель). **Права:** read — `base.group_user`; запис — через sudo-service; повний доступ — `geodata_manager` (Додаток 4).

---

### 3.2 `dm.geodata.address.mixin` (AbstractModel) — спільна логіка інтеграцій
**Поля:** `geodata_address_id` (M2o `dm.geodata.address`, ondelete=`set null`, copy=False); `geodata_autocomplete_active` (Boolean, store=False); `area`/`hromada` (Char); related-документні readonly (`address_full_ua/en`, `address_letter_ua/en`, `kato`, `koatuu`, `terr_status`, координати); `has_geodata_credential`, `geodata_show_manual_hint`, **`geodata_show_area`/`geodata_show_hromada`** (compute, compute_sudo — дзеркала тумблерів credential для `invisible` у view).

**Узагальнення (фундамент для будь-якої моделі з адресою):** уся owner-side логіка винесена з `res.partner` у міксин і **не залежить від назв полів** — керується картою `_geodata_fields` (логічний рівень → реальне поле; дефолт — стандартні назви). У міксині: `_geodata_is_ua`, `_GEO_CLEAR_BELOW`/`_GEO_DETACH_LEVELS`/`_GEO_ADDRESS_LEVELS`, `_geodata_clear_block`/`_geodata_detach`/`_geodata_live_sync`/`_geodata_onchange`, `_norm`, `_geodata_sync_on_manual_change`/`_is_house_only_change`, `write()` (sync + 1:1 GC), `_geodata_owner_values` (ремап стандартних ключів `to_address_values` у реальні поля). Декоратори `@api.onchange(...)` оголошує **кожен інтеграційний модуль** для своїх реальних полів (міксин їх не хардкодить). Онбординг нової моделі: `_inherit` міксина (+ за потреби `_geodata_fields`) + тонкі onchange-обгортки + view. `res.partner` — еталон; crm.lead (стандартні назви) / hr.employee (`private_*`) / res.bank (`state`/`country`) — додаються тонкими модулями.

**Методи (entry-points для віджета, доступні `base.group_user`):**
- `autocomplete_cities(query, dep_values)` / `autocomplete_streets(query, dep_values)` — нормалізують запит (`strip`+collapse) **до** `min_chars`, dedup по trimmed-query, короткий кеш; повертають підказки.
- `apply_address(record_id, api_data)` — **sudo-service**: для власника без прив'язки `create_from_api` (новий приватний рядок), інакше `update_from_api` у власний рядок → `fetch_en_translit` (1×) → запис у запис-власник із `context(geodata_applying=True)`. При відчепленні/видаленні власника приватний рядок видаляється (`write`/`unlink` міксина).
- `_clear_geodata_link()` + хелпери ієрархічного очищення — з **UX-захистом #16** (див. 3.6).

> **Рішення #1/#2:** усі звернення до `dm.geodata.address`/`dm.geodata.api.credential` усередині цих методів — через `sudo()`; виклик самих методів **не вимагає** спец-групи.

---

### 3.3 `dm.geodata.api.credential` (Model) — власні креденшали (без kw_*)
**Поля:** `name` (Char, `_sql_constraints` unique), `active` (Boolean), `company_id` (M2o res.company), `api_url` (Char), `api_username` (Char), `api_password` (Char), `store_english` (Boolean, default True), **`show_old_names`** (Boolean, default False — дужкові старі назви в адресних полях/форматах), **`show_area`/`show_hromada`** (Boolean, default False — показ полів Район/Громада на формах; лише відображення, дані заповнюються незалежно), `address_format_document`/`address_format_letter` (Char), `debounce_ms` (Integer, default 300), `min_chars` (Integer, default 3), `cache_ttl_s` (Integer, default 60), `payment_notification_interval` (Integer).
- `access_token` — **НЕ у звичайному полі**: зберігати в `ir.config_parameter` (ключ `geodata.access_token.<id>`, читання/запис sudo) або через шифрування (#11).

**Методи:**
- `_api_request(method, endpoint, params, silent)` — власний `requests`-клієнт: `timeout` (конфіг, default 60), **обмежений retry лише на 401** (refresh token → 1 повтор), без back-off-штормів; **маскований лог** (Authorization/паролі → `***`, #15).
- `_refresh_token()`, `get_credential(company=None)` — фільтр `active=True` + company fallback (#15.3).
- API-обгортки: `api_full_address`, `api_cities`, `api_streets`, `api_houses`, `api_address` (нормалізація пробілів усередині — #17).
- `action_test_connection`, `action_sync_ukraine_states` (виклик синку явно).
- `_check_address_format` (`@api.constrains`) — валідні плейсхолдери.
- `write` — при зміні логіна/пароля скидає токен; **НЕ робить `search([])`-recompute адрес** (#6) — формати перераховуються через depends.

**Права:** read — `geodata_user`; повний — `geodata_manager`. **`ir.rule` company-isolation** (#4).

---

### 3.4 `base.geocoder` (override) — провайдер геокодування
- `_call_geodata(addr)` — повертає координати; **без side-effect create** `dm.geodata.address`/`res.country.state` (#10): створення станів — лише в явному синку.
- `_geo_query_address_geodata(...)`, `_validate_coordinates(lat, lon, strict_ukraine)`.
- `res.partner.geo_localize` — **без перемикання глобального** `ir.config_parameter` (#9): провайдер обирається локально для набору.

---

### 3.5 Інтеграційні моделі (тонкі)
- `res.partner` (`dm_geodata_contact`): `_inherit = ["res.partner", "dm.geodata.address.mixin"]`; нові `area`, `hromada` (Char); related-документні поля; inline-autocomplete на `street`/`city`; ієрархічні onchange/`write`-хелпери з UX-захистом (#16). **Без `action_open_geodata_wizard`.** `area`/`hromada` у формі — у самому адресному блоці тим самим механізмом, що й City/State (`.o_address_format` — block; клас `o_geodata_addr_col`: `display:inline-block; width:48%; margin-right:2%`). Селектор **обов'язково** під `.o_form_editable .o_address_format .o_geodata_addr_col` — щоб збігтися зі специфічністю ядрового правила ширини (інакше `width:48%` перекривається назад до повної ширини й поля стають у стовпчик). НЕ flex/grid — це block із inline-block-полями. Інтеграцію застосовано **і до головної форми** (`base.view_partner_form`), **і до діалогу дочірньої адреси** (Доставка/Рахунок/Інше). Діалог на вкладці «Контакти та адреси» — це **inline-форма всередині `child_ids`** у `view_partner_form` (xpath scoped `//field[@name='child_ids']//div[@name='div_address']`), а не `view_partner_address_form`; останню теж розширено (для потоків, що її використовують). У діалозі — **лише autocomplete (city/street) + area/hromada**; рядок пошуку та документні деталі НЕ додаються (вони лише на головній формі, вкладка Address Information), щоб не ламати компактний діалог.
- **Реалізовані тонкі модулі:** `dm_geodata_crm` (`crm.lead`, стандартні назви) і `dm_geodata_company` (`res.company`) — обидва наслідують міксин зі стандартною картою + onchange-обгортки + view. Гейт країни у view — через **рідне `country_code`** (`res.company` його має; `crm.lead` — нема, тож модуль додає related-поле `country_code = country_id.code`). Нюанс `res.company`: адресні поля — compute/inverse до `partner_id` (текст спільний із партнером), але Geodata-лінк — власний для компанії (1:1 на власника).
- **Пакування (умбрела):** `dm_geodata_online` — застосунок-умбрела (`depends=[dm_geodata_connector]`). Інтеграції `dm_geodata_contact`/`dm_geodata_crm`/`dm_geodata_company` — **auto_install-мости**, що залежать від `dm_geodata_online` (+ свого додатку: contacts/crm). Встановлення `dm_geodata_online` → мости авто-ставляться (де є відповідний додаток); видалення `dm_geodata_online` → каскадом знімає мости; ядро `dm_geodata_connector` лишається (знімається окремо).
- `hr.employee` (`private_*`) / `res.bank` (`state`/`country`) / `lunch.supplier` (related через partner) — додаються за тим самим рецептом за потреби.

---

### 3.6 Поведінка синхронізації блок ↔ документні поля (виправлення #16)
- Через Geodata (autocomplete) — як раніше: заповнює і запис-власник, і `dm.geodata.address`, документні поля наповнюються.
- **Ручне редагування:** замість «мовчазного» скидання — **попередження** (alert у формі) + збереження документних полів до **явного** «Скинути адресу» (кнопка) АБО `onchange`-повідомлення «адресу змінено вручну — Geodata-дані застаріли». Координати/коди не зникають без підтвердження.

---

## 4. ВИМОГИ ДО БЕЗПЕКИ

### 4.1 Групи
- `geodata_user` — адміністрування довідника адрес (опц.).
- `geodata_manager` (implied user) — конфіг `dm.geodata.api.credential`, синк станів.
- Autocomplete/ingestion — доступні **усім internal users** (`base.group_user`) через sudo-service.

### 4.2 ACL-матриця (`ir.model.access.csv`)
| Модель | base.group_user | geodata_user | geodata_manager |
|---|---|---|---|
| `dm.geodata.address` | R | R,C | R,W,C,U |
| `dm.geodata.api.credential` | — | R | R,W,C,U |
| `dm.geodata.request.log` | — | R | R,U |
> Запис у `dm.geodata.address` під час ingestion — через `sudo()` у service-шарі (а не через user-ACL).

### 4.3 Row-Level Security (`ir.rule`) — #4
- `dm.geodata.address`: `['|',('company_id','=',False),('company_id','in',company_ids)]` (додати `company_id` на адресу або успадкувати через власника) — мульти-компанійна ізоляція.
- `dm.geodata.api.credential`: company-rule (`company_id in company_ids` або global).

### 4.4 Інше
- Токен/паролі — не в логах (маскування), токен — у `ir.config_parameter`/шифр (#11/#15).
- Санітизація вводу autocomplete (нормалізація, обмеження довжини, `[:N]` результатів).
- Немає HTTP-контролерів → CORS не застосовний; усі виклики — внутрішній ORM RPC.

### 4.5 Захист секретів платного акаунта (v1.4.3, Варіант A)
- Меню «API Credentials» — лише `group_geodata_manager`.
- ACL `dm.geodata.api.credential` — лише manager (read для `group_geodata_user` прибрано).
- `api_username`/`api_password` — `groups="base.group_system"` → ORM віддає їх лише Settings-адмінам
  (не читаються через RPC/export/форму ні plain-користувачем, ні не-system менеджером).
- Серверні потоки читають секрети через `sudo()` (`_refresh_token`), тож autocomplete і Test Connection
  працюють без розкриття секретів. (#11/#15)
- **Опційно B (майбутнє):** винести `api_password` у `ir.config_parameter` як write-only (як токен).

---

## 5. ПЛАН ТЕСТУВАННЯ (ціль 95%+, окремий `dm_test_geodata_connector`, mock API)

| ID | Сценарій | Тип | Очікуваний результат |
|---|---|---|---|
| TC-001 | `create_from_api` створює **новий** рядок щоразу (без дедуплікації) | unit | два однакові payload → два різні рядки |
| TC-002 | Повторний `upsert` тим самим ключем | unit | **без дубля** (#12) — той самий запис оновлено |
| TC-003 | `apply_address` як **звичайний** user (base.group_user) | security | успіх (sudo-service); без AccessError (#1/#2) |
| TC-004 | Multi-company: user компанії A не бачить адрес B | security | `ir.rule` приховує (#4) |
| TC-005 | Форматування `address_full_ua/en` (mock credential) | unit | очікувані рядки UA/EN |
| TC-006 | Ручне редагування міста після Geodata | unit/UX | документні поля **не зникають мовчки** (#16) |
| TC-007 | Нормалізація пробілу: «Київ» vs «Київ » | unit | **один** API-виклик (dedup), не два (#17) |
| TC-008 | `min_chars`/`strip` до перевірки довжини | unit | `< min_chars` після strip → `[]` |
| TC-009 | area/hromada — readonly auto-fill | unit/tour | заповнюються з вибору; немає виклику неіснуючих методів (#3) |
| TC-010 | Токен не потрапляє в лог | unit | у `dm.geodata.request.log` Authorization = `***` (#15) |
| TC-011 | `_api_request` 401 → refresh → 1 повтор | unit (mock) | один retry, без шторму (#3.8.2) |
| TC-012 | `create` адреси **без** мережі | unit | успіх; жодного HTTP у `create` (#5) |
| TC-013 | Tour: inline-autocomplete місто→вулиця, save | HttpCase | місто не очищується після вулиці; коди заповнені |
| TC-014 | `get_view` форми credential (Odoo 19) | unit | контекст EN-сторінки коректний (#8) |

Гранична обробка: порожній recordset, архівний credential (фільтр active), відсутність credential, не-UA країна, batch-import (без HTTP).

---

## 6. ПЛАН РОЗГОРТАННЯ

- **Залежності (Odoo 19 CE):** `base`, `base_geolocalize`, `web`; інтеграції — `contacts`, `crm`, `hr`, `lunch` (кожна — у своєму тонкому модулі). **Зовнішніх Python-пакетів** понад штатний `requests` немає (задекларувати `external_dependencies.python=['requests']`).
- **Інсталяція:** `dm_geodata_connector` → `post_init_hook` синхронізує області у `res.country.state` (idempotent, помилки логуються рівнем warning, не debug).
- **Конфіг:** Settings → Geodata.online → credential (username/password) → Test Connection (UserInfo + Balance).
- **Міграція зі старої версії (опц.):** скрипт `migrations/19.0.1.0.0/post-migration.py` — перенос `dm.geodata.address` (відкинути `*_ru`-поля), monikers; backup перед міграцією; перевірка цілісності (кількість адрес, прив'язки partner).
- **Розгортання:** self-hosted Linux, PostgreSQL; реліз як набір модулів; `dm_geodata_online` — для App Store.

---

## 7. ДОДАТКИ

### 7.1 Матриця аудиту → рішення (повна, 17 + cleanup)
| ID | Опис (стара версія) | Коренева причина | Рішення в новому модулі | Статус |
|---|---|---|---|---|
| AU-001 | `dm.geodata.address` write=0 для user, але apply пише без sudo | Невідповідність ACL ↔ потоку запису | sudo-service для запису довідника | ✅ |
| AU-002 | Autocomplete-методи недоступні не-geodata користувачам | Модель за спец-групою | методи доступні `base.group_user` | ✅ |
| AU-003 | Виклик неіснуючих `kw_autocomplete_areas/hromadas` (5 модулів) | Незавершений рефакторинг | area/hromada readonly auto-fill | ✅ |
| AU-004 | Немає `ir.rule` (multi-company) | Пропущена ізоляція | company-rules + `_check_company` | ✅ |
| AU-005 | HTTP у ORM `create` + множник у майстрі | Зовнішній I/O у create | ingestion лише в on_select; без wizard | ✅ |
| AU-006 | `credential.write` → recompute усіх адрес | Ручний `search([])` | depends-driven recompute | ✅ |
| AU-007 | `get_credential()` у циклі (N+1) | Виклик у форматері | credential як параметр | ✅ |
| AU-008 | `fields_view_get` (мертвий у 17+) | Застарілий API | `get_view`/`_get_view` | ✅ |
| AU-009 | Глобальний `geo_provider` race | Глобальний стан | локальний вибір провайдера | ✅ |
| AU-010 | Side-effect create станів | Запис у read-подібних | стани лише в явному синку | ✅ |
| AU-011 | Токен/пароль відкритим текстом у БД | Без захисту секретів | токен у config_parameter/шифр | ✅ |
| AU-012 | Немає `_sql_constraints`/дедупу | Відсутність ключа | unique-ключ + dedup у upsert | ✅ |
| AU-013 | demo вантажиться як `data` | Невірний ключ маніфесту | demo → ключ `demo` | ✅ |
| AU-014 | Hardcoded рядки без `_()` | Пропущена i18n | `_()` + `.pot` | ✅ |
| AU-015 | Токен у HTTP-логах headers | Логування headers як є | маскування Authorization | ✅ |
| AU-016 | Мовчазне очищення документних адрес | Безумовний unlink | попередження/збереження до явного скидання | ✅ |
| AU-017 | Запити по пробілу (дубль) | Немає debounce/dedup/strip | debounce300+dedup+strip до min_chars | ✅ |
| CL-01 | **Wizard — мертвий код** (`action_open_geodata_wizard` без UI-кнопки) | Незавершена відмова від функції | у новому модулі **відсутній повністю** | ✅ |
| CL-02 | `_update_from_ua_translation` (0 call-site) | Залишок | не переносити | ✅ |
| CL-03 | Дубль `dm_geodata_online` (модель+view) | Copy-paste | meta-bundle порожній | ✅ |

### 7.2 Посилання
- Odoo 19 ORM / `get_view` / security (ACL, record rules) / OWL field widgets / `base_geolocalize`.

### 7.3 Глосарій
- **KOATUU** — старий класифікатор адмінодиниць; **KATOTTG (kato)** — новий (2020+).
- **Hromada** — територіальна громада. **Moniker** — токен сесії пошуку Geodata (місто/вулиця) для подальших запитів.
- **Ingestion** — приймання й нормалізація відповіді API у `dm.geodata.address`.

---

## 8. ЗМІНИ v1.1 (фідбек тесту + уточнений API-контракт)

Після першого встановлення тест виявив 10 дефектів. У `doc/` додано офіційні API-файли
(`API_Cities/Streets/Houses/Address_*`), що уточнили контракт. Нижче — рішення.

### 8.1 Уточнений API-контракт (ланцюг монікерів і поля підказок)
- **Cities** → `st_moniker` (монікер міста) + **`CityString`** (готовий текст підказки).
- **Streets** (param `stMoniker` = `st_moniker`) → `house_moniker` + **`StreetString`**.
- **Houses** (param `houseMoniker` = `house_moniker`) → **`HouseString`** (= HouseNum+HouseNumAdd).
- **Address** (one-line) → **`AddressString`** (повна адреса; для поля пошуку на вкладці).
- Монікери живуть 15 хв; протермінування → HTTP 400 `{"message":"Moniker expired"}` → підказки `[]`.
- Поля `*String` **не зберігаються в БД** — лише для наповнення випадаючих списків.

### 8.2 Матриця дефект → рішення
| # | Дефект | Рішення |
|---|---|---|
| 1 | Пошук іде при країні ≠ Україна | Country-gate: server-методи повертають `[]`, якщо країна не Україна. `_geodata_country_ok(dep)` приймає `dep.country_code == 'UA'` **або** `dep.country_id == base.ua` (надійно для будь-якої моделі — `country_id` завжди є в адресному блоці, тоді як related `country_code` на crm.lead/res.company у дані форми не завжди потрапляє). dep_values несе і `country_code`, і `country_id`. Клієнтський `countryOk` пускає пошук, коли `country_code` порожній/відсутній (рішення за `country_id` — на сервері). |
| 2 | Нова картка — країна не UA | `res.partner.default_get` ставить `base.ua` |
| 3 | Немає підказок вулиць після міста | Монікер міста передається у dep як `geodata_city_moniker` (Char на власнику), не лише через m2o; вулиці беруть його з dep |
| 4 | Немає підказок будинків | Роутинг у `geodata_autocomplete_streets`: при наявному `geodata_street_moniker` і номері після назви вулиці → `api_houses` |
| 5 | Підказка міста | label/value = `CityString` |
| 6 | Підказка вулиці | label/value = `StreetString` |
| 7 | Підказка будинку | label = `StreetString` + ", " + `HouseString` (`StreetString` беремо з поля `geo.street_string`, бо у Houses-відповіді його немає) |
| 8 | Вкладка не наповнюється | `apply_address` **merge** у ТУ САМУ `dm.geodata.address` (`update_from_api`); m2o встановлюється у форматі Odoo 19 `{id, display_name}` |
| 9 | Немає пошуку на вкладці | Поле `geodata_search` з віджетом → `geodata_autocomplete_full_address` (api/Address, `AddressString`) |
| 10 | Немає переходу до деталі | Перехід через internal-link readonly-поля `geodata_address_id` (форма `dm.geodata.address`). Метод `action_view_geodata_address` лишається доступним, але кнопки на формі немає |

### 8.3 Технічні уточнення до розділів 3
- **3.1 `dm.geodata.address`**: новий `update_from_api(api_data)` — merge наданих полів у існуючий запис (без HTTP/create), щоб ланцюг city→street→house тримав ОДИН запис.
- **3.2 mixin**: нові поля `geodata_city_moniker`, `geodata_street_moniker` (Char, **store=False** — транзитивний стан форми, НЕ нові колонки res.partner; довговічна копія на `dm.geodata.address`, fallback `_linked_moniker`), `geodata_search` (store=False); **причина non-stored:** нові stored-колонки на res.partner валять Odoo 19 web-Upgrade country pre-check (`button_install` префетчить усі stored partner-поля до `_auto_init`); методи `geodata_autocomplete_full_address`, `_format_*_suggestion` на базі `*String`, house-routing у `geodata_autocomplete_streets`, `apply_address(record_id, api_data, current_address_id)` з merge, `action_view_geodata_address`.
- **3.5 view**: вкладка «Address Information» (UA-мітка «Інформація про адресу») отримує поле пошуку (api/Address); перехід до деталі — через internal-link поля `geodata_address_id` (без окремих кнопок «Full Address»/«Reset Geodata»); country-gate `invisible="country_code != 'UA'"`. EN-адреса на формі контакту показується завжди (вміст — за `store_english`).
- **3.5a порядок адресного блоку**: `div.o_address_format` у bridge-формах отримує клас `o_geodata_address_grid`; connector-SCSS робить його `display:flex` з явними `order` (Місто, Область, Район, Громада, Індекс, Країна) — детерміновано, без залежності від inline-block переносу теми. `hr.employee` — звичайний group (порядок за DOM).
- **OWL widget**: m2o у `record.update` — об'єкт `{id, display_name}` (підтверджено вихідником Odoo 19 `relational_model/record.js`); dep_values несе `country_code`, **`country_id`**, монікери, `city`/`street`.

### 8.3a Уточнення v1.2 (другий раунд фідбеку)
| # | Дефект | Рішення |
|---|---|---|
| 1 | Поле «Search Address» не тримає вибране для прогресивного пошуку | Опція віджета `progressive`: `onSelect` вставляє `suggestion.value` у власне поле; api/Address — free-form, тож ввід продовжується (місто→вулиця→будинок) |
| 2 | «Область» не автозаповнюється | `dm.geodata.address._resolve_state_id()` (search-only по `res.country.state`, `_normalize_region_name`); `to_address_values` повертає `state_id` |
| 3 | Фільтр `sRegion` не працює | `geodata_autocomplete_cities` бере регіон із `dep.state_id` (browse→normalize name), а не з display_name; віджет передає `state_id` (id) |
| 4 | Підказки будинків | Лейбл = **`geo.street_string`** (поле `StreetString`, як його віддає API — зі старими назвами в дужках, **незалежно від `show_old_names`**) + `HouseString`. У Houses-відповіді `StreetString` немає, тож беремо збережений на адресі. `_build_street_label` лишається лише для **детекції** house-режиму (`raw.startswith(clean_label)`), а не для лейбла |

### 8.3b Уточнення v1.3 (UX випадаючого списку)
Лише фронтенд OWL-віджета `geodata_autocomplete` (JS/QWeb/SCSS); бекенд/API без змін.
| # | Дефект | Рішення |
|---|---|---|
| 1 | Список відрізняється від штатного / теми не діють / нема підсвітки | Chrome списку — штатні Bootstrap `dropdown-menu`/`dropdown-item` (без захардкоджених кольорів). **Підсвітка** активного/наведеного пункту — тими самими **Sass-змінними**, що й ядровий `AutoComplete` (`$dropdown-link-hover-color/-bg`, як `a.ui-state-active` у `web/.../core/autocomplete/autocomplete.scss`). Важливо: Odoo **не емітить** Bootstrap-CSS-змінні `--bs-dropdown-*`, тож підхід через `var(--bs-dropdown-…)` дає **порожню** підсвітку — використано Sass-значення (compile-time, підхоплюють тему бандла). Класи `o-autocomplete--*` для нас інертні (стилі ядра scoped під `.o-autocomplete`) |
| 2 | Немає навігації клавіатурою | `state.activeIndex` + `onKeydown` (на полі, фокус лишається в input): ↑/↓ циклічно (preventDefault), Enter обирає активний/перший (без сабміту форми), Escape закриває; `onItemHover` синхронізує з мишкою; `_scrollActive()` скролить активний у видиму зону. Активний пункт несе клас `focus`. Список авто-закривається по `pointerdown` **поза** віджетом (`useExternalListener`), не лише на blur |
| 3 | Список вужчий за довгі підказки (текст переноситься/обрізається) | Ширина списку — **по контенту**, незалежно від ширини полів: SCSS `width:max-content`, `min-width:100%`, `max-width:min(40rem,90vw)`, item `white-space:nowrap`+ellipsis з повним текстом у `title`; JS `_positionSuggestions` робить right-flip (`left:auto;right:0`) при виході за правий край viewport. Ширина полів не змінюється |

### 8.3c Уточнення v1.4 (оформлення як у старому модулі + повний набір полів)
- **Повний набір полів API:** `dm.geodata.address` зберігає **всі** поля з відповідей API — UA+EN+**RU**
  (RU зберігається, але поки не показується/не фетчиться) + старі назви, метро, suburb, *String,
  source_query, address_level, comments/description. Мапінг — `_api_data_to_vals` (за зразком старого).
- **Координати (#4):** building (`latitude/longitude`) — лише коли payload несе `HouseNum/HouseId/Street`;
  інакше координати → settlement (`latitude_settlement/...`). Відсутні координати = `None` (омітяться),
  тож merge не затирає попередні (house-крок зберігає settlement міста).
- **Форма «Address»** оформлена як у старому: сторінки Administrative (Address + Codes and Status),
  Coordinates (Building/Settlement), English Transliteration, Metro, Old Names, Additional, Documents.
  Вкладку **Ids прибрано** з форми (поля лишаються на моделі). Мітки полів населеного пункту містять «населеного пункту» (#2). Порядок
  правого стовпця «Old Names» (#3): Старий тип н.п. → Стара назва н.п. → Старий тип вулиці → Стара назва
  вулиці. Форма read-only (`edit/create="false"`).
- **Вкладка «Address Information»**: бордер-бокс пошуку, групи «Address details»
  (readonly `geodata_address_id` з internal-link на форму адреси, KATOTTG/KOATUU/повні адреси —
  `widget="CopyClipboardChar"`, `geodata_address_updated`; **без кнопок «Full Address»/«Reset Geodata»**
  і без рядка «Verified up to»), «Full Addresses for Documents/Letters» (UA/EN, copy), посилання
  geodata.online. RU-рядки прибрані (UA+EN).
- `CopyClipboardChar` — штатний віджет Odoo 19 CE (`web`), застосовано до Char-полів.

### 8.3e Уточнення v1.4.3 (захист логіна/пароля платного API — Варіант A)
- Прибрано read `group_geodata_user` на `dm.geodata.api.credential` (тільки manager).
- `api_username`/`api_password` → `groups="base.group_system"` (ORM-read лише Settings-адмін).
- `_refresh_token` читає секрети через `self.sudo()` → autocomplete/Test Connection працюють,
  секрети не розкриваються. Деталі — §4.5. Опційно B (config_parameter write-only) — на майбутнє.

### 8.3d Уточнення v1.4.2 (меню Request Log)
- Додано пункт **Settings → Geodata.online → Request Log** (manager-only):
  `views/geodata_request_log_views.xml` — list/form/search для `dm.geodata.request.log`
  (URL, method, HTTP status, duration, params, headers[masked], error; filter «Errors»,
  group by method/status/day). Дія `geodata_request_log_action`, menuitem `menu_geodata_request_log`
  (parent `menu_geodata_root`, groups `group_geodata_manager`). Python/модель/ACL без змін
  (модель і права вже існували з v1.0). Headers лишаються маскованими (#15).

### 8.3f Уточнення v1.5 (синхронізація адреси: verified-only + індикатор + re-resolve)
Модель узгодженості блок ↔ `dm.geodata.address`:
- **Verified-only:** у `dm.geodata.address` зберігаються лише перевірені (вибрані з підказок) рівні; рівень —
  за ref-ами `settlement_ref`/`street_ref`/`house_ref`. Ручні значення нижчих рівнів — лише в блоці.
- **Clear-down (#4):** `update_from_api` визначає рівень payload (`_api_level`) і чистить нижчі
  (`_CLEAR_BELOW_CITY`/`_CLEAR_BELOW_STREET`) — нове місто скидає стару вулицю/будинок.
- **Downgrade/Detach (#1/#2/#3):** `res.partner.write` порівнює нові значення блоку з валідованими
  (`geo.to_address_values()`); зміна населеного пункту/області/району/громади → **detach**; зміна вулиці →
  **downgrade** (house-only лишає вулицю валідованою). + `@api.onchange` чистять залежні поля блоку наживо
  (guard `geodata_autocomplete_active`). Спільна мапа `_GEO_CLEAR_BELOW`: зміна/видалення населеного
  пункту очищає й **похідні `area`/`hromada`** (вони приходять разом із містом), а також street/zip —
  і в onchange (UI), і у `write` (save/RPC).
- **Документні адреси = лише перевірене (3a)**; `geodata_verified_level` (none/settlement/street/house)
  лишається **обчислюваним**, але на формі **не показується** (дублював індикатор «і»).
- **Індикатор ручних даних:** `credential.show_manual_hint` (вмикач); computed `geodata_city_verified`/
  `geodata_street_verified`; OWL-віджет малює **одну бурштинову іконку «і»** з підказкою (без рамки) лише
  коли поле **непорожнє**, рівень неперевірений **і країна = Україна** (`isManual` строго перевіряє
  `country_code === 'UA'`) — бо модуль працює тільки з українськими адресами.
- **Авто re-resolve монікерів (без кнопок) (#2/#4):** `credential._resolve_city_moniker`/
  `_resolve_street_moniker` (за KATOTTG/refs); `geodata_autocomplete_streets` прозоро поновлює
  протермінований монікер і повторює запит один раз.

### 8.4 Тести (dm_test_geodata_connector)
Мок повертає `CityString`/`StreetString`/`HouseString`/`AddressString` + `st_moniker`/`house_moniker`.
Покрито: country-gate (#1), ланцюг city→street→house з одним записом (#3-#8), full-address search (#9),
підказки з *String (#5/#6/#7), залежність вулиць від монікера міста (#3), resolve `state_id`,
чистий house-лейбл (v1.2 #4). UX-зміни v1.3 — лише браузерна перевірка (не покривається unit-тестами).

---

*Кінець BLUEPRINT v1.5.* Покриває 17 знахідок `doc/AUDIT.md` + 3 cleanup + 10 пунктів фідбеку (v1.1)
+ 4 уточнення (v1.2) + 2 UX-зміни списку (v1.3) + оформлення як у старому модулі та повний набір полів
API (v1.4); відображає рішення замовника (no kw_*, no wizard; RU зберігається, але не показується)
і узгоджений з офіційним API-контрактом Geodata.online.
