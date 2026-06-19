# ТЕХНІЧНИЙ FORENSIC-АУДИТ: odoo-ukraine-address-directory

> Цільова версія — **Odoo 18.0** (гілка `18.0`, `version: 18.0.x`). Оцінка проти 18.0; готовність до 19/20 — окремо (С.12).
> Обмеження: зовнішні залежності `kw_api_connector`, `kw_widget_autocomplete`, `kw_mixin`, `kw_http_request_log`, `generic_mixin` (з `kitworks-systems/addons`, `crnd-inc`) у репозиторії відсутні — їх поведінка позначена [UNKNOWN]/[ASSUMED].

---

## СЕКЦІЯ 0. PRE-FLIGHT INVENTORY

### 0.1–0.2 Дерево та призначення (код-файли, без static/description PNG)

| Модуль | Тип шару | Ключові файли (рядків) |
|---|---|---|
| `dm_geodata_connector` | Core | `models/geodata_address.py` (1550), `geodata_api_credential.py` (1259), `geodata_address_mixin.py` (224), `base_geocoder.py` (83), `geodata_api_connector.py` (11); `tools/ukraine_states_sync.py` (221); 3 міграції; `data/res_country_state_ukraine.json` (282); security (csv 7 ряд. + xml 20); 3 view (214+178+56) |
| `dm_geodata_contact` | UI | `models/res_partner.py` (692), `wizards/geodata_address_wizard.py` (295), `static/src/js/geodata_autocomplete_patch.js` (42), 2 view, security csv (3), 1 міграція |
| `dm_geodata_company` | Integration | `models/res_company.py` (53), view (72) |
| `dm_geodata_online` | Meta | `models/res_company.py` (53, дубль), view (72, дубль) |
| `dm_geodata_crm` | Integration | `models/crm_lead.py` (19), view (135) |
| `dm_geodata_hr` | Integration | `models/hr_employee.py` (47), view (76) |
| `geodata_lunch` | Integration | `models/lunch_supplier.py` (59), view (72) |
| `dm_test_geodata_connector` | Tests | 6 тест-файлів (≈1900 ряд.), 2 mock-моделі, demo (2 xml), tour JS, security csv |

### 0.3 Очікуване, але ВІДСУТНЄ

| Очікувано | Стан | Примітка |
|---|---|---|
| `tests/` у проді-модулях | Відсутнє реально | Тести лише в `dm_test_geodata_connector` |
| `migrations/` | Частково: лише в `dm_geodata_connector` (3), `dm_geodata_contact` (1) |
| `i18n/*.po` | Є `uk.po` у 6 модулях; **немає `.pot`**; інтеграційні модулі — лише 22-ряд. заглушка |
| `security/` | Немає у `dm_geodata_crm/hr/lunch/company/online` (покладаються на ACL базових моделей) |
| `controllers/` | Відсутнє реально — HTTP-контролерів немає (підтверджено grep) |
| `ir.cron`, `mail.template`, `ir.rule` | Відсутнє реально (grep — 0 збігів) |
| `static/description/` | Є (cover/icon/index.html + image*.png) |

### 0.4 Висновок про достатність
Матеріалів достатньо для повного аудиту бізнес-логіки, security, ORM, views. Обмеження — лише `kw_*` фреймворк (зовнішній), що впливає на верифікацію HTTP-рівня та JS-віджета.

---

## СЕКЦІЯ 1. ЗАГАЛЬНА ІНФОРМАЦІЯ

### 1.1 Метадані (`dm_geodata_connector/__manifest__.py`)
`name`: "Ukraine Address Reference Directory" · `version`: **18.0.2.5.0** · `author`: DM Solutions · `license`: **LGPL-3** · `category`: Hidden · `website`: geodata.online · `application`: False · `installable`: True · `auto_install`: False · `post_init_hook`: post_init_hook. Відсутні: `maintainer`, `support`, `price`, `currency`, `sequence`.

### 1.2 Семантика version
[CONFIRMED] Формат `18.0.2.5.0` — коректний 5-компонентний Odoo-формат, узгоджений з гілкою 18.0. **Розсинхрон версій:** connector 2.5.0, contact 2.1.0, company/crm/hr/lunch 1.1.0, online 1.0.0. `doc/ARCHITECTURE.md:89` каже "connector v18.0.2.0.0" — **документація застаріла**.

### 1.3 Бізнес-призначення [CONFIRMED]
Інтеграція з зовнішнім API **Geodata.online** (`https://api.dmsolutions.com.ua:2661`, `data/geodata_api_connector.xml:5`) для автодоповнення/нормалізації українських адрес: модель-сховище `dm.geodata.address` (90+ полів), покрокове autocomplete (місто→вулиця→будинок) через JS-віджет, прив'язка до `res.partner/company/crm.lead/hr.employee/lunch.supplier`, геокодування через `base.geocoder`, синхронізація областей у `res.country.state`.

### 1.4 Дублювання стандарту Odoo
[CONFIRMED] Перевизначає провайдера геокодування `base.geocoder` (`base_geocoder.py:10`) — штатна точка розширення. Поля `area`/`hromada` — нові. Дублювання штатного функціоналу немає.

### 1.5 Ознаки legacy / copy-paste

| Ознака | Локація | Мітка |
|---|---|---|
| Override `fields_view_get` — метод видалено в Odoo 17+ (замінено `get_view`) | `geodata_address.py:393-412` | [CONFIRMED] мертвий код у 18.0 |
| Майже повний дубль `res_company.py` | `dm_geodata_company` ≡ `dm_geodata_online` | [CONFIRMED] copy-paste |
| Дубль view з тим самим `name`/xpath | `dm_geodata_company/...res_company_views.xml` ≡ `dm_geodata_online/...` | [CONFIRMED] |
| Дубль методів `_get_field_by_lang` ≡ `_get_old_name_by_lang` | `geodata_address.py:647-664` | [CONFIRMED] |
| Дубль `_build_translation_query` ≡ `_build_translit_query` | `geodata_address.py:1253-1293` | [CONFIRMED] |
| Артефакт кодування `учше#` | `doc/ARCHITECTURE.md:1` | [CONFIRMED] |
| `@api.one/@api.multi/@api.returns` | відсутні (grep 0) | [CONFIRMED] позитив |

---

## СЕКЦІЯ 2. АНАЛІЗ МАНІФЕСТУ (ядро)

### 2.1 Ключі

| Ключ | Значення | Ризик | Примітка |
|---|---|---|---|
| `depends` | base, base_geolocalize, kw_api_connector | Low | див. 2.2 |
| `external_dependencies.python` | `[]` | Medium | Код використовує `requests` (`geodata_api_credential.py:4`) — не задекларовано |
| `data` | 8 файлів | Low | порядок коректний (security→data→views) |
| `demo` | порожньо | Info | |
| `assets` | `web.assets_backend: scss/*` | Low | Odoo 17+ синтаксис коректний |
| `post_init_hook` | `post_init_hook` | Medium | див. 2.7 |

### 2.2 depends
[CONFIRMED] `base_geolocalize` використовується (`base_geocoder.py:10`, `res_partner.py:265`). `kw_api_connector` — `_inherit=["kw.api.credential"]`/`["kw.api.connector"]`. **Прихована залежність:** `bus.bus` (`geodata_api_credential.py:198`) [ASSUMED транзитивно]. `requests` — не в depends.

### 2.3 data files
[CONFIRMED] Усі 8 файлів існують, порядок правильний. Файлів у репо, не вказаних у `data`, не виявлено (крім свідомо порожнього `demo`).

### 2.4 demo
Ядро — без demo. **Проблема в test-модулі:** `dm_test_geodata_connector/__manifest__.py:18-22` вантажить `demo/*.xml` через ключ **`data`**, а не `demo` → demo-записи інсталюються завжди.

### 2.7 hooks
[CONFIRMED] `post_init_hook` (`dm_geodata_connector/__init__.py:9-30`) синхронізує області з JSON у `res.country.state`.
- **Idempotency:** так (`ukraine_states_sync.py:187-205`).
- **uninstall_hook:** відсутній → orphan `res.country.state`/`dm.geodata.address` (С.9).
- **Глушіння помилок:** усі except логуються рівнем `.debug` (`__init__.py:30`) — збій синку невидимий у стандартних логах. [CONFIRMED] Low.

---

## СЕКЦІЯ 3. ПОВНИЙ ПЕРЕЛІК ФУНКЦІОНАЛУ

### 3.1 Моделі

| Технічна назва | Тип | Inherit | Файл | _order | Призначення |
|---|---|---|---|---|---|
| `dm.geodata.address` | Model | — | `geodata_address.py:40` | `create_date desc` | Сховище адрес (90+ полів) |
| `dm.geodata.address.mixin` | AbstractModel | — | `geodata_address_mixin.py:8` | — | Спільна логіка autocomplete |
| `dm.geodata.api.credential` | Model | `kw.api.credential` | `geodata_api_credential.py:12` | — | OAuth-креденшали |
| `geodata.api.connector` | Model | `kw.api.connector` | `geodata_api_connector.py:8` | — | Endpoint API |
| `base.geocoder` | AbstractModel | `base.geocoder` (override) | `base_geocoder.py:9` | — | Провайдер геокодування |
| `res.partner` | Model | `+dm.geodata.address.mixin` | `res_partner.py:9` | — | Партнер + адреса |
| `dm.geodata.address.wizard(.result)` | TransientModel | — | `geodata_address_wizard.py:24,250` | — | Майстер пошуку |
| `crm.lead`/`res.company`/`hr.employee`/`lunch.supplier` | Model | + mixin/related | відповідні | — | Інтеграції |
| `geodata.api.response.mock`/`...credential.tour` | Model | (test) | test-модуль | — | Тестова інфраструктура |

### 3.2 Поля (вибірково)
`dm.geodata.address`: ~90 Char/Float/Boolean + 7 computed store=True (`name`, `address_string`, `address_ua_postal/short/western`, `address_full_*`, `address_letter_*`). Індекси: `settlement_ref`, `street_ref`, `house_ref`. `translate=True` на `region/area/city/...`. **`geodata_id` без index**, хоч шукається (`base_geocoder.py:54`).

**kw-успадковані поля `dm.geodata.api.credential`** (з `kw.api.credential`, `kw_api_connector/models/credential.py`): `name` (з **unique** sql-constraint, `:19-21`), `active`, `company_id`, `api_connector_id`, `code` (related→connector.name, store), `type`; а також **delegate**-поля з `kw.http.request.log.source` (`is_log_enabled`, `log_retention_period`, `type`) через `delegate=True` mixin (`http_request_log_source.py:80-84`). Кожне створення credential **авто-створює** запис `kw.http.request.log.source` (`:89-100`). Поля `api_key` **немає** (С.13.3).

### 3.3 Бізнес-логіка

**3.3.1 CRUD overrides:**
- `dm.geodata.api.credential.write` (`:127-138`) — скидає `access_token` при зміні логіна/пароля; **при зміні формату адрес `search([])` + `_compute_full_addresses()` для ВСІХ адрес** — критична точка продуктивності.
- `dm.geodata.api.credential.default_get` (`:140-146`).
- `res.partner.default_get` (`:165-176`), `res.partner.write` (`:560-586`) — складна логіка очищення геоданих.
- `dm.geodata.address.wizard.create` (`@api.model_create_multi`, `:125-138`) — **викликає `action_search()` (HTTP + create) усередині `create`** — антипатерн.
- `fields_view_get` (`:393`) — мертвий у 18.0.

**3.3.2 Action-методи:** `action_test_connection`/`action_sync_ukraine_states`/`action_search`/`action_select_and_apply`/`action_select` → dict; `action_refresh_api_token_geodata` → bool. Типи коректні.

**3.3.3 Constraints:** лише `@api.constrains("address_format_document","address_format_letter")` (`:105-125`). **SQL-constraints відсутні** → жодного унікального ключа на `dm.geodata.address`.

**3.3.4 Computed:** `@api.depends` повні. Результат `_compute_full_addresses` залежить ще й від `credential.store_english/russian` (`:508-510`), яких немає в depends → перемикання прапорця не інвалідує кеш (тому ручний recompute у `write`).

**3.3.5 Onchange:** `res_partner.py:199-252` — 5 onchange каскадного очищення; write/create не роблять — коректно. Дублює серверне очищення у `write`.

**3.3.6** `@api.model_create_multi` — у wizard.

**3.3.7 Момент транслітерації/перекладу [CONFIRMED]:** транслітерація EN та переклад RU **не привʼязані до збереження картки** — `res.partner.write` їх не запускає. Точка входу `fetch_translations()` (`geodata_address.py:1374`) викликається **лише** з `create_from_api_response` (`:1040`) та `update_from_api_response` (`:1190`), тобто в момент **ingestion даних з API**:
1. вибір підказки autocomplete → `apply_address_to_partner`/`apply_geodata_address` → `_resolve_geodata_address` (`mixin:116-118`);
2. пошук у майстрі → `action_search` (`wizard:177-188`);
3. геокодування → `geo_localize` (`base_geocoder.py:58`).
Усередині `fetch_translations`: EN лише при `store_english`, RU лише при `store_russian` → **до 2 синхронних HTTP-запитів на адресу**, у request-транзакції (повʼязано з #5).
Наслідки:
- **Множник у майстрі:** `action_search` транслітерує **кожен новий** результат списку → пошук на N нових адрес = до **N×2 запитів** ще до вибору користувачем (Performance/Cost).
- **Перемикання прапорця не «доганяє» наявні адреси:** `credential.write` лише переформатовує (`_compute_full_addresses`), **не довантажує** переклади старих записів (`credential.py:134-137`) — переклад залишиться порожнім, доки адресу знову не оновлять з API.
- **Save лише переформатовує:** computed `address_full_*`/`address_letter_*` читають уже збережені `_en/_ru`, нових запитів не роблять.
- **Мертвий код:** `_update_from_ua_translation` (`:1331`) визначено, але ніде не викликається (0 call-site).

### 3.4 Views
- `attrs=`/`states=` — відсутні [CONFIRMED] позитив. `<list>` скрізь. Чатера на `dm.geodata.address` немає (коректно).
- **xpath:** `crm_lead_views.xml:10,20` використовує позиційний `//div[hasclass('o_address_format')][1]` — крихкий.
- `groups=`: `base.group_no_one` на сторінці Ids (`geodata_address_views.xml:133`).

### 3.5 Меню та actions

| xml_id | parent | groups |
|---|---|---|
| `menu_geodata_root` | `base.menu_administration` | `group_geodata_manager` |
| `menu_geodata_api_credential/connector/address` | root | (connector: `base.group_system`) |

### 3.6 Безпека

**3.6.1 ACL (`dm_geodata_connector/security/ir.model.access.csv`):**

| model | group | R | W | C | U |
|---|---|---|---|---|---|
| geodata.api.connector | user / manager | 1/1 | 0/1 | 0/1 | 0/0 |
| dm.geodata.api.credential | user / manager | 1/1 | 0/1 | 0/1 | 0/1 |
| **dm.geodata.address** | **user** | **1** | **0** | **1** | **0** |
| dm.geodata.address | manager | 1 | 1 | 1 | 1 |

**КЛЮЧОВИЙ КОНФЛІКТ [CONFIRMED]:** `group_geodata_user` має на `dm.geodata.address` **write=0**, але потоки `apply_address_to_partner`→`_resolve_geodata_address`→`update_from_api_response`→`self.write(...)` (`geodata_address_mixin.py:116`, `geodata_address.py:1189`) пишуть у `dm.geodata.address` без sudo. Autocomplete-застосування завершується успішно лише для manager-групи. Звичайний `group_geodata_user` → `AccessError`. (С.7 #1)

**3.6.2 Record rules (`ir.rule`):** ВІДСУТНІ [CONFIRMED]. `dm.geodata.address`/`dm.geodata.api.credential` не ізольовані по company. (С.7 #4)

**3.6.3 Groups:** `group_geodata_user`, `group_geodata_manager` (implied user; users=root,admin); категорія `module_category_hidden`. Звичайним користувачам група не призначається → autocomplete недоступний (виклик методів `dm.geodata.api.credential` → AccessError). (С.7 #2)

**3.6.4 sudo()-мапа (22 виклики connector+contact):**

| Місце | Виправдання | Ризик |
|---|---|---|
| `get_credential().sudo()` у compute/`fields_view_get` | Читання конфігу | Низький (read) |
| `State.sudo().create()` (`geodata_address.py:1438`, `ukraine_states_sync.py:150`) | Створення довідкових областей | Помірний |
| `geo_addr.sudo().write({"city_moniker"...})` (`mixin:1180,1236`) | Кеш monikers | Маскує проблему 3.6.1 частково |
| `self.sudo().write({"access_token"...})` (`credential:283`) | Збереження токена | Виправдано |

### 3.7 Автоматизації
[CONFIRMED] Власних cron/mail.template/server actions/base.automation/queue_job у geodata-модулях немає. Уся робота — синхронна, в request-транзакції. **Уточнення:** інфраструктура логування з `kw_http_request_log` додає щоденний cron `cron_delete_outdated_logs` (`kw_http_request_log/data/ir_cron.xml`, model `kw.http.request.log`) — він і чистить логи геодата-запитів за `log_retention_period=30`.

### 3.8 API та інтеграції
**3.8.1 Controllers:** відсутні.
**3.8.2 External HTTP:** прямий `requests.post` лише для токена (`geodata credential:271-276`, timeout=60). Решта — через `self.api_request(...)` (модель `kw.api.credential`, **тепер верифіковано** `kw_api_connector/models/credential.py:87-186`): `timeout=60` хардкод, **єдиний retry лише при token-refresh** (`is_refresh_api_token_needed` → `action_refresh_api_token`), без back-off/повторів на 5xx/мережеві; параметр `silent` керує raise-vs-`False`. Geodata-token-refresh без retry, глобальний `except Exception` (`geodata credential:296`).
**3.8.3 HTTP-логування:** кожен `api_request` пише запис у `kw.http.request.log` (URL, method, **headers**, params, request/response body) — у **новій транзакції** (`generic.mixin.transaction.utils`). ⚠️ Headers містять `Authorization: Bearer {token}` → витік токена в логи (С.7 #15).
**3.8.4 Token storage:** `access_token`/`api_password` Char у БД відкритим текстом (`geodata credential:49,44`) + токен у логах headers (#15). (С.7 #11, #15)

### 3.9 Дані
- `base.geo_provider`, `geodata.api.connector`, `kw.http.request.log.source` — без `noupdate` → перезапис при upgrade (`api_url` адміна скинеться). Low.
- demo-креденшал `active=False` (безпечно), але вантажиться як `data`.
- `ir.config_parameter`: `base_geolocalize.geo_provider` (тимч. перемикання), `geodata.test.mock_api` (тест).

### 3.10 Frontend
- OWL patch `KwAutocompleteField` (`geodata_autocomplete_patch.js:12`) — `patch(...prototype)`, перехоплює `onSelect`. Legacy JS — немає. SCSS присутні. Monkey-patch зовнішнього віджета — крихкий (С.12.3).

### 3.11 Wizards
`dm.geodata.address.wizard(.result)` — TransientModel, GC стандартний. Антипатерн: `create` запускає HTTP-пошук.

### 3.12 Reports
Відсутні.

### 3.13 Translations
- `translate=True` на ~12 полях + `area/hromada`. **Конфлікт:** одночасно зберігаються переклади в окремих полях `_en/_ru` (через API) **і** Odoo-`translate=True` — дві паралельні системи перекладу. Medium.
- `.pot` відсутні. **Hardcoded без `_()`:** `"кв."` (`:731,817`), `"УКРАЇНА"` (`:529-531`). Low.

---

## СЕКЦІЯ 4. ЗМІНИ СТАНДАРТНИХ МОДЕЛЕЙ ODOO

### 4.1 Таблиця втручань

| Модель | Тип | Нові поля | Override методи | Файл |
|---|---|---|---|---|
| `base.geocoder` | extension | — | `_call_geodata`, `_geo_query_address_geodata`, `_validate_coordinates` | `base_geocoder.py` |
| `res.partner` | extension + mixin | area, hromada, geodata_search, ~25 related, geocoding_source | `default_get`, **`write`**, `geo_localize`, 5×onchange | `res_partner.py` |
| `res.company` | extension (×2!) | area, hromada, 5 related | `apply_geodata_address` | company/online |
| `crm.lead` | extension + mixin | area, hromada, country_code | — | crm_lead.py |
| `hr.employee` | extension + mixin | private_area, private_hromada, private_country_code | `_build_geodata_vals` | hr_employee.py |
| `lunch.supplier` | extension | area, hromada, 5 related | `apply_geodata_address` | lunch_supplier.py |

### 4.2 Аналіз override-методів
- `res.partner.write` (`:560`): super().write коректно у звичайній гілці; **гілка multi-record (`_apply_geodata_coords:548-558`) робить super().write у циклі** і повертає True, оминаючи фінальний super — N писань + розбіжність single vs multi. Medium. Нескінченної рекурсії немає.
- `base.geocoder._call_geodata`: **side-effect** — створює `dm.geodata.address` під час геокодування (`:57-60`). Medium.
- `res.partner.geo_localize`: тимчасово перемикає глобальний `ir.config_parameter` геопровайдера, повертає у `finally` (`:264-271`) — **race при паралельному geo_localize**. Medium.
- **Синхронізація адресний блок ↔ вкладка «Інформація про адресу» [CONFIRMED]:** звʼязок **односторонній** — поля вкладки `related="geodata_address_id.*"` readonly (`:99-163`) лише віддзеркалюють привʼязаний `dm.geodata.address`. Заповнюються/оновлюються **лише** коли адресу задано через Geodata (autocomplete/майстер, `geodata_autocomplete_active=True`). **Ручне** редагування адресного блоку **не переносить нові значення у вкладку**, а **розриває звʼязок і очищає вкладку**: onchange `_clear_geodata_link()` при зміні міста/країни (`:221,243`) — миттєво до save; `_update_geodata_on_address_change`→`partner.geodata_address_id=False` на save для зміни рівня область/район/громада/вулиця (`:490-529`). **Єдиний виняток** — зміна **тільки № будинку** на тій самій вулиці (`house_only`, `:505-526`): звʼязок зберігається, у `geo_addr` оновлюється будинок. Наслідок — «мовчазне очищення» документних/листових адрес, KATOTTG, KOATUU, координат при будь-якому ручному редагуванні (С.7 #16, С.15.13). UX/Medium.

### 4.3 Зони підвищеного ризику
- `res.partner` — центральна: важкий `write` з зовнішнім I/O-наслідками; mixin зі зворотним записом у `dm.geodata.address` (ACL-конфлікт 3.6.1).
- `hr.employee` private-поля під `groups="hr.group_hr_user"` — коректно.
- `account.move`/`stock.*`/`sale.order` — не торкаються [CONFIRMED] позитив.

### 4.4 Conflict matrix
- Конфлікт xpath з модулями, що чіпають `res.partner.street/city` widget або `o_address_format`.
- Конкуренція за глобальний `geo_provider` з іншими `base.geocoder`-провайдерами (OCA).

---

## СЕКЦІЯ 5. АРХІТЕКТУРА ТА ЯКІСТЬ КОДУ

### 5.1 Conventions
[CONFIRMED] Іменування/структура — відповідає Odoo. Pylint/flake8/isort/pre-commit налаштовані — позитив.

### 5.2 Code smells

| Smell | Локація |
|---|---|
| Файл-гігант 1550 ряд. | `geodata_address.py:1` |
| Дублювання методів/файлів/views | 1.5 |
| Метод-монстри: `_api_data_to_vals` (~145), `to_address_dict` (~78), `kw_autocomplete_streets` (~70) | `:885`, `:1463`; `mixin:1075` |
| Magic-координати меж України | `base_geocoder.py:22` |
| Велетенські статичні мапи очищення (200+ ряд.) | `res_partner.py:294-419` |
| Hardcoded `"кв."`, `"УКРАЇНА"` | 3.13 |

### 5.3 Stability
- **`create` з HTTP** (wizard `:135`) + **`create_from_api_response` → `fetch_translations` → до 2 синхронних HTTP** (`geodata_address.py:1040`). Таймаут API → збій create. Транслітерація йде в момент ingestion, не на save (С.3.3.7); у майстрі множиться на кількість нових результатів (до N×2 запитів).
- Race на глобальному geo_provider (4.2).
- `credential.write` → recompute усіх адрес.
- `env.cr.commit()` у бізнес-логіці — відсутній [CONFIRMED] позитив. Savepoints не використовуються.

---

## СЕКЦІЯ 6. ЗАЛЕЖНОСТІ ТА ІНТЕГРАЦІЇ

### 6.1–6.2 Графи
```
dm.geodata.api.credential ──api_request──> kw.api.connector ──HTTP──> Geodata.online
        ▲ get_credential()
dm.geodata.address.mixin ──> dm.geodata.address ──find_or_create──> res.country.state
        ▲                          ▲
res.partner / crm.lead / hr.employee (M2o geodata_address_id)
res.company / lunch.supplier ──related──> partner_id.geodata_address_id
base.geocoder ──> dm.geodata.address
```

### 6.3 Coupling
- `dm.geodata.address` — high fan-in (усі інтеграції + geocoder + wizard).
- `dm.geodata.address.mixin` — high fan-out.
- `res.partner.apply_address_to_partner` — викликається company/online/lunch.

### 6.4 Cascade impact
Зміна `apply_address_to_partner`/`to_address_dict`/`_GEODATA_FIELD_MAP` → каскад у 6+ файлів. Зміна `_FIELD_API_KEYS` → впливає на фільтрацію в усіх потоках.

---

## СЕКЦІЯ 7. ПОТЕНЦІЙНІ РИЗИКИ (за severity)

| # | Severity | Категорія | Файл:line | Опис | Тригер | Наслідок | Recommendation |
|---|---|---|---|---|---|---|---|
| 1 | High | Security/Stability | `ir.model.access.csv:6` + `mixin:116`,`address:1189` | `group_geodata_user` write=0 на `dm.geodata.address`, але apply-потік пише без sudo | Не-manager обирає підказку | `AccessError`, autocomplete не застосовується | Дати write=1 user-групі або контрольований `sudo()` |
| 2 | High | Security/UX | `geodata_security.xml`, views | Autocomplete-методи на `dm.geodata.api.credential`; модель недоступна не-geodata-користувачам | Звичайний sales/HR редагує адресу | `AccessError`/порожня підказка | Розширити read-доступ або призначати групу; задокументувати |
| 3 | High | DataIntegrity/Functionality | `dm_geodata_company/online/crm/hr/lunch` views | Виклик **неіснуючих** `kw_autocomplete_areas`/`kw_autocomplete_hromadas` | Введення ≥3 символів у area/hromada | RPC-помилка у 5 модулях | Реалізувати методи або прибрати widget |
| 4 | High | Security/Multi-company | відсутність `ir.rule` | Немає record rules на `dm.geodata.address`/`credential` | 2+ компанії | Витік адрес/креденшалів | Додати company-rules |
| 5 | High | Stability | `geodata_address_wizard.py:125-138`, `geodata_address.py:1040` | HTTP у ORM `create` | Створення адреси / autocomplete | Збій create при недоступному API | Винести у явні методи, async/queue |
| 6 | Medium | Performance | `geodata_api_credential.py:134-137` | `search([])` + recompute усіх адрес у `write` | Зміна формату адреси | На 100k адрес — багатосекундна блокуюча транзакція | Recompute батчами/cron/тільки змінені |
| 7 | Medium | Performance | `geodata_address.py:630,642` | `get_credential()` у циклі recompute (N+1) | Масовий recompute | N зайвих SELECT | Передавати credential параметром |
| 8 | Medium | Upgrade | `geodata_address.py:393` | Override `fields_view_get` — мертвий у 18.0 | Відкриття форми address | RU-сторінка завжди прихована; контекст не працює | Перейти на `get_view`/`_get_view` |
| 9 | Medium | Stability | `res_partner.py:264-271` | Глобальний `geo_provider` перемикається на час geo_localize | Паралельний geo_localize | Race: чужі партнери не тим провайдером | Локальний провайдер/блокування |
| 10 | Medium | DataIntegrity | `geodata_address.py:1438`, `:57` | Side-effect create `res.country.state`/`dm.geodata.address` | Apply/geocode | Зростання довідників, дублі станів | Винести у явні write |
| 11 | Medium | Security | `geodata_api_credential.py:49,283` | `access_token`/`api_password` відкритим текстом | — | Витік при доступі до БД/бекапу | Шифрування/secrets |
| 12 | Medium | DataIntegrity | відсутність `_sql_constraints` | Немає унікальності `dm.geodata.address` | Повторні/паралельні apply | Дублі адрес | Унікальний індекс або dedup |
| 13 | Low | Maintainability | `dm_test_geodata_connector` demo як `data` | demo вантажиться в проді | Інсталяція тест-модуля | Зайві записи | Перенести у ключ `demo` |
| 14 | Low | i18n | 3.13 | hardcoded рядки без `_()` | — | Неперекладні "кв."/"УКРАЇНА" | Обгорнути/винести |
| 15 | Medium | Security | `kw_api_connector/credential.py:122` + `geodata get_api_headers_geodata` | `api_request` логує `headers` з `Authorization: Bearer {access_token}` у `kw.http.request.log.headers` (`is_log_enabled=True`, retention 30 днів) | Будь-який лог-ований запит до API | Витік access-токена всім із read на `kw.http.request.log` (~30 днів) | Маскувати `Authorization` перед логуванням або вимкнути логування headers (повʼязано з #11) |
| 16 | Medium | UX/DataIntegrity | `res_partner.py:221,243,490-529` | Ручне редагування адресного блоку розриває звʼязок і **мовчки очищає** вкладку «Інформація про адресу» (повні/листові адреси, KATOTTG, KOATUU, координати), окрім зміни лише № будинку | Користувач вручну править місто/вулицю/область/індекс після Geodata-заповнення | Зникнення документних адрес/кодів без попередження; повторне наповнення лише через Geodata | Показувати попередження/підтвердження перед очищенням або зберігати документні поля до явного скидання (С.4.2, С.15.13) |
| 17 | Medium | Performance/Cost | `geodata_api_credential.py:706,346-364` (cities); `:471-489` (full); `:870-894` (streets) | **Запити по пробілу:** немає debounce/dedup; перевірка `len(query)<3` — до обрізання; `api_cities_search` **не робить strip** → «Київ» і «Київ » = два різні платні запити з ідентичним результатом; багатослівний ввід шле запит на кожен пробіл | Натискання пробілу / зайві пробіли при ≥3 символів | Зайві платні запити до Geodata.online (дубль для міста), пришвидшене вичерпання балансу (402) | Нормалізувати/`strip` запит **до** перевірки довжини у всіх `autocomplete_*`; dedup «пропустити, якщо `query.strip()` не змінився»; підтвердити клієнтський debounce у `kw_widget_autocomplete` (С.15.14) |

---

## СЕКЦІЯ 8. РЕКОМЕНДАЦІЇ ЩОДО РЕФАКТОРИНГУ

**8.1 Quick wins (<1 дня):** видалити мертвий `fields_view_get`→`get_view` (#8); прибрати дубль `dm_geodata_online/res_company.py`+view; demo→`demo` (#13); `_()` для hardcoded (#14); об'єднати дубль-методи.

**8.2 Critical fixes (до production):** #1 (ACL write на address), #2 (доступ до autocomplete), #3 (неіснуючі area/hromada методи), #4 (multi-company record rules).

**8.3 Desired (середній термін):** #5 (HTTP поза create), #6/#7 (recompute), #9 (race geo_provider), #11 (шифрування токена).

**8.4 Technical debt:** декомпозиція `geodata_address.py`; єдина система перекладів (`_en/_ru` АБО `translate=True`).

**8.5 Decomposition:** форматування адрес → окремий AbstractModel/util; `_PARTNER_GEO_CLEAR_MAP`-логіка → mixin.

**8.6 Test plan:** С.13.

---

## СЕКЦІЯ 9. ОЦІНКА СКЛАДНОСТІ ЗМІН

| Блок | Складність | Ризик регресії | Залежні | Коментар |
|---|---|---|---|---|
| `dm.geodata.address` форматування | Середня | Середній | усі інтеграції | Добре покрите тестами |
| `res.partner.write/onchange` | Висока | Високий | company/lunch/crm/hr | Складна мапа очищення |
| autocomplete потік | Висока | Високий | JS+credential+mixin | Залежить від kw |
| Інтеграційні views | Низька | Середній | — | Крихкі xpath |

- **Safe to upgrade (мінор):** з умовами — `noupdate`-config перезапишеться; recompute у write важкий.
- **Safe to uninstall:** Ні — немає `uninstall_hook`; orphan `dm.geodata.address`, `res.country.state`, monikers.
- **Data migration:** міграції охайні, idempotent SQL — позитив.

---

## СЕКЦІЯ 10. ВИСНОВОК

**10.1** Модуль функціонально багатий, добре структурований за шарами, з ретельними `@api.depends`, охайними міграціями та пристойним тестовим покриттям форматування/сценаріїв. Водночас містить блокуючі production дефекти: ACL-конфлікт запису в `dm.geodata.address`, недоступність autocomplete для звичайних користувачів, виклики неіснуючих методів area/hromada у 5 модулях, відсутність multi-company ізоляції, синхронні HTTP у ORM-`create`.

**10.2 Production readiness: `Not ready`** (Conditional після усунення #1–#5).

**10.3 Maintainability:** середня. Плюс — конвенції, lint, міграції, тести; мінус — файли-гіганти, дублювання, дві системи перекладу.

**10.4 Scalability:** до ~кількох тис. адрес — ОК. ≥50–100k — `credential.write`-recompute (#6) і N+1 (#7) дають багатосекундні блокування. Autocomplete-латентність — від зовнішнього API.

**10.5 Security posture:** слабка — токени/паролі відкритим текстом, немає record rules, плутанина ACL, широкі `sudo()` create.

**10.6 Upgrade 18→19/20:** Medium — `fields_view_get` мертвий, крихкі xpath, monkey-patch JS-віджета.

**10.7 Стратегічна рекомендація:** Incremental refactor — виправити блокери #1–#5/#8, прибрати дублювання `dm_geodata_online`, уніфікувати переклади. Повного rewrite не потрібно.

**10.8 Сильні сторони (підтверджені):**
1. Чисто шарова архітектура з AbstractModel-mixin та делегуванням.
2. Сучасний синтаксис Odoo 17/18: `<list>`, `invisible`-domain, `model_create_multi`, без `@api.one/multi`, без `cr.commit`.
3. Охайні idempotent-міграції з raw-SQL.
4. Розгорнуті `@api.depends` + шаблонізатор адрес із валідацією плейсхолдерів.
5. Реальне unit-покриття форматування/сценаріїв через mock.

---

## СЕКЦІЯ 11. DEEP ORM ANALYSIS

- **11.1** `ensure_one()` правильно (`:823,1044,1374`); `filtered` (`res_partner.py:281`); `browse([])`-edge через `.exists()`.
- **11.2 create:** `@api.model_create_multi` лише у wizard; super().create повертає recordset коректно.
- **11.3 write:** антипатерн write-in-loop — `_apply_geodata_coords` (`res_partner.py:549-556`).
- **11.4 search:** `search([])` без limit (`credential:135`); `wizard:183` limit=1 — добре.
- **11.5 compute:** depends повні; `geodata_id` без index; recompute залежить від не-depends-джерела (credential).
- **11.6 onchange:** не пишуть/не створюють — позитив.
- **11.7 sudo/context:** `with_context(geodata_applying=True)` — навмисний обхід `write`-логіки.
- **11.8 cache:** `invalidate_recordset(["geodata_address_id"])` (`mixin:97`) обґрунтовано.
- **11.9 N+1:** `get_credential()` у циклі recompute (#7).
- **11.10 Direct SQL:** лише в міграціях, **параметризовано** (`%s`) — захист від інʼєкцій є.
- **11.11 Transaction:** `cr.commit()` відсутній — позитив.

---

## СЕКЦІЯ 12. UPGRADE IMPACT ANALYSIS

**12.1 Deprecated:** `attrs/states`, `<tree>`, `@api.one/multi/returns`, old assets — немає. **АЛЕ `fields_view_get`** (`:393`) видалено в 17+ → мертвий код.
**12.2 xpath:** позиційні `[1]` (`crm_lead_views.xml:10,20,50`); `dm_geodata_online` дублює inherit базової форми компанії → подвійне додавання тих самих полів.
**12.3 Monkey-patch:** JS `patch(KwAutocompleteField.prototype)` — ризик при оновленні `kw_widget_autocomplete`.
**12.4 Core overrides:** `res.partner.write`, `base.geocoder` — середній; account/stock/sale не торкаються.
**12.5 Python:** 3.10+ синтаксис, без анотацій — сумісно.
**12.6 Складність 18→19→20:** Medium.
**12.7 Версії kw_*-залежностей [CONFIRMED у цьому checkout]:** `kw_api_connector` 16.0.0.6.0, `kw_http_request_log` 16.0.0.5.0, `kw_mixin` 16.0 — manifest-версія **Odoo 16**, тоді як geodata цілиться у **18.0**. Перед апгрейдом перевірити, що використовується 18.0-сумісна гілка `kitworks-systems/addons`; інакше — ризик несумісності зовнішнього фреймворку, на якому тримається все ядро (С.17).

---

## СЕКЦІЯ 13. TEST COVERAGE MATRIX

### 13.1 Інвентаризація

| Файл | Тип | Підхід |
|---|---|---|
| `test_address_format.py` | TransactionCase | mock (`patch get_credential`) — 24 тести |
| `test_address_scenarios.py` | TransactionCase | mock `mock_api_data.json` |
| `test_step_by_step_input.py` | TransactionCase | mock покрокового вводу |
| `test_hierarchy.py` | TransactionCase | без API — каскадне очищення |
| `test_geodata_integration.py` | TransactionCase | live API (skip без credential) + unit |
| `test_tour.py` | HttpCase/Tour | mock через config_param |

### 13.2 Покриття

| Компонент | Тести | Покриття |
|---|---|---|
| Форматування адрес | mock | Повне |
| Каскадне очищення partner | є | Часткове |
| apply_address_to_partner | unit | Часткове |
| autocomplete streets/houses moniker-retry | немає | Немає |
| ACL/security/multi-company | немає | Немає |
| area/hromada autocomplete | немає | Немає (методів не існує — #3) |
| credential.write recompute | немає | Немає |

### 13.3 КОНФЛІКТ ТЕСТІВ vs КОД [CONFIRMED]
- `test_geodata_integration.py:345` — `test_partner.has_geodata_address` — поле НЕ існує (grep) → `AttributeError`.
- `:389` — `apply_geodata_address(geodata_address)` проти сигнатури `apply_geodata_address(record_id, api_data)` (`mixin:211`) → `TypeError`.
- `:44` — `credential.api_key` — **[CONFIRMED]** поля `api_key` **немає** у `kw.api.credential` (поля: name, active, company_id, api_connector_id, code, type + delegate-лог; `kw_api_connector/models/credential.py:23-42`) → `AttributeError`.
→ Інтеграційні тести застарілі (узгоджуються зі застарілим `doc/TESTING_PLAN.md`).

### 13.4 Safety без тестів
Зміни у `res.partner.write`/мапах очищення — небезпечні без нових тестів краю. Уникати правок autocomplete-moniker без HttpCase. Форматування — відносно безпечно.

---

## СЕКЦІЯ 14. FINAL TECHNICAL SCORECARD

### 14.2 Scorecard

| Категорія | Оцінка | Обґрунтування |
|---|---|---|
| Architecture | 🟢 | Чітка шаровість, mixin, делегування |
| Code quality | 🟡 | Lint+конвенції, але файли-гіганти/дублі |
| ORM usage | 🟡 | Сучасно; write-in-loop, N+1 recompute, HTTP в create |
| Security | 🔴 | ACL-конфлікт write (#1), немає record rules (#4), токени відкрито в БД (#11) та в HTTP-логах headers (#15) |
| Performance | 🟡 | recompute-усіх (#6), N+1 (#7), синхронний API |
| Data integrity | 🟡 | Немає sql-constraints (#12), side-effect create (#10) |
| Maintainability | 🟡 | Дублювання, дві системи перекладів |
| Upgrade readiness | 🟡 | Мертвий `fields_view_get`, крихкі xpath, JS-patch |
| Test coverage | 🟡 | Гарний mock-шар, але застарілі інтеграційні тести (13.3), 0 security-тестів |
| Documentation | 🟡 | Є ARCHITECTURE/README/TESTING_PLAN, але застарілі версії/поля |
| Production readiness | 🔴 | Блокери #1–#5 |

### 14.3 Risk score

- Security: #1 High(18), #4 High(18), #11 Medium(9), #15 Medium(9) = 54
- DataIntegrity: #3 High(18), #10 Medium(9), #12 Medium(9), #16 Medium(9) = 45
- Upgrade: #8 Medium(6) = 6
- Performance: #6(4.5), #7(4.5), #9(4.5), #17 Medium(4.5) = 18
- Code quality: дублювання ~3 = 3
- Test gaps: 13.3 + security = 6
- Stability #5 High(9) = 9

**Σ ≈ 141 → Score = min(100, 141) = `100` → критичний ризик (81–100)**, керований security+data-integrity вагами ×3. Без security (-54) → 87 → все ще критичний. Пріоритет №1 — security-блокери.

### 14.4 Executive summary
- Модуль зрілий за функціоналом і архітектурою, але не готовий до production через конкретні дефекти.
- **Топ-3 проблеми:** (1) autocomplete не зберігається для не-адмінів через ACL `write=0`; (2) у 5 модулях area/hromada викликають неіснуючі методи → помилка користувачу; (3) немає ізоляції даних між компаніями.
- **Топ-3 сильні сторони:** шарова архітектура; сучасний Odoo-18 синтаксис; idempotent-міграції + mock-тести.
- **Go/No-Go:** No-Go до виправлення блокерів; після — Conditional Go.
- **Стратегія:** інкрементальний рефакторинг (не rewrite).
- **Складність підтримки:** Medium.

---

## СЕКЦІЯ 15. EDGE CASE & FAILURE MODE ANALYSIS

- **15.1 Multi-company:** `credential.company_id` + fallback (`credential:627-656`) є; record rules немає → читання чужих даних (#4). `_check_company` відсутній.
- **15.2 Multi-currency:** не застосовно.
- **15.3 Archived:** `wizard.credential_id` domain `active=True`; `get_credential` **не фільтрує `active`** (`credential:643`) — може повернути архівований. Low.
- **15.4 Empty recordset:** `.exists()`/`ensure_one()` оброблено.
- **15.5 Batch:** `create_from_api_response` приймає один dict; HTTP у create ламає import/batch (#5).
- **15.6 Recursive triggers:** нескінченної рекурсії немає (4.2).
- **15.7 Async/queue:** відсутній.
- **15.8 i18n:** подвійна система перекладів (С.4); hardcoded рядки; транслітерація/переклад — за подією ingestion, не на save, з множником у майстрі (С.3.3.7).
- **15.9 Timezone:** `fields.Date.context_today` (`wizard:218`) коректно.
- **15.10 Duplicate detection:** немає sql-constraints; dedup лише пошуком limit=1 → race при паралельному create (#12).
- **15.11 Portal:** не розширює portal.
- **15.12 Performance великих наборів:** `search([])` recompute (#6); autocomplete `[:15]` (`mixin:1028`) — добре.
- **15.13 Синхронізація адресний блок ↔ вкладка «Інформація про адресу» [CONFIRMED gap]:** напрям лише `dm.geodata.address → вкладка` (related readonly). Очікувана поведінка «змінив адресу вручну → вкладка показує нову адресну інформацію» **не реалізована**: ручне редагування трактується як «це більше не валідована Geodata-адреса» → звʼязок розривається, вкладка (повні/листові адреси, KATOTTG, KOATUU, переклади, координати) **мовчки порожніє**. Виняток — зміна тільки № будинку (`house_only`). Деталі — С.4.2; ризик — С.7 #16.
  - **Failure mode:** користувач формує договір із заповненою «Повною адресою (UA)», потім вручну править, напр., індекс/вулицю → документні поля зникають без попередження; повторне наповнення можливе лише через повторний вибір у Geodata.
- **15.14 Запити по пробілу (cost) [CONFIRMED]:** автодоповнення робить API-запит і при натисканні пробілу (немає debounce/dedup; `len(query)<3` перевіряється до `strip`). Для поля «місто» `api_cities_search` **не нормалізує** пробіли → «Київ» і «Київ » — два окремі **платні** запити з тим самим результатом; багатослівний ввід шле запит на кожен пробіл. Деталі — С.7 #17; повʼязано з відсутністю debounce/ліміту (попередній аналіз) і множником у майстрі (С.3.3.7).

---

## СЕКЦІЯ 16. MISSING EVIDENCE & ASSUMPTIONS REGISTER

**16.0 ВИРІШЕНО (після прочитання kw_*-модулів у `addons/`):**
- Поведінка `api_request`: timeout=60, single token-refresh retry, без back-off (С.3.8.2).
- 401/refresh-флоу: `parse_api_error_geodata`→`is_refresh_api_token_needed`→retry один раз (`credential.py:175-180`).
- `credential.api_key` — поля немає → тест впаде (С.13.3).
- Ланцюг залежностей + AbstractModel-природа kw-моделей (С.17.0).

**16.1 Бракує для повного аудиту (досі):**
- Вихідники `kw_widget_autocomplete` (JS-віджет, формат `dep_values`, чи sudo при виклику методів) та `generic_mixin` (`generic.mixin.transaction.utils`).
- Реальний формат відповіді Geodata.online API.

**16.2 Висновки на [ASSUMED]:**
- Доступність `bus.bus` без явного depends (С.2.2).
- ACL-наслідок #1/#2 для виклику методів credential — підтверджую логічно (ACL-модель Odoo), остаточно — live-тест із не-адмін користувачем.

**16.3 Питання до автора:**
1. Чи autocomplete доступний лише користувачам у групі Geodata? Якщо так — чому запис у `dm.geodata.address` під user-групою з `write=0`?
2. Чи `dm_geodata_online` має дублювати view/модель `res.company` при залежності від `dm_geodata_company`?
3. Де реалізація `kw_autocomplete_areas/hromadas`, на які посилаються 5 view-файлів?
4. Чи свідомо вимкнено multi-company record rules?
5. Чи актуальні `test_geodata_integration.py` тести (`has_geodata_address`, `apply_geodata_address(addr)`)?

---

## СЕКЦІЯ 17. АНАЛІЗ ЗОВНІШНІХ `kw_*` ЗАЛЕЖНОСТЕЙ

> Оновлено: 3 з 4 модулів прочитано у `C:\work\DM\git\addons\` (`kw_api_connector`, `kw_http_request_log`, `kw_mixin`). Відсутні вихідники: `kw_widget_autocomplete`, `generic_mixin`.

### 17.0 Ланцюг залежностей (підтверджено маніфестами)
```
dm_geodata_connector
  └─ kw_api_connector (16.0.0.6.0)            [kw_api_connector/__manifest__.py:12-14]
        └─ kw_http_request_log (16.0.0.5.0)   [kw_http_request_log/__manifest__.py:13-16]
              ├─ generic_mixin (crnd-inc)
              └─ kw_mixin (16.0)
```
Отже `kw_http_request_log`, `generic_mixin`, `kw_mixin` — **гарантовано транзитивні** (а не «приховані»: завантажуються разом із `kw_api_connector`). `kw.api.connector` і `kw.api.credential` — **AbstractModel** (`connector.py:8`, `credential.py:13`); geodata робить їх concrete.
**Версійна невідповідність [CONFIRMED у цьому checkout]:** усі kw_* мають manifest-версію **16.0.x** при цілі geodata **18.0** (С.12.7).

### 17.1 Таблиця модулів

| # | Модуль | Джерело / версія | Надає | Точка інтеграції в коді | У `depends`? | Тип звʼязку | Критичність | Ризик / примітка |
|---|---|---|---|---|---|---|---|---|
| 1 | **`kw_api_connector`** | kitworks / 16.0.0.6.0 | `kw.api.connector`, `kw.api.credential` (AbstractModel); `api_request` (`credential.py:87`), `get_api_url/headers`, `code`/`type`, диспетчер `use_fname` | `geodata_api_connector.py:10`, `geodata_api_credential.py:14` (`_inherit`) | Так — `dm_geodata_connector` | Python `_inherit` | Критична (ядро) | Без нього `dm_geodata_connector` не вантажиться |
| 2 | **`kw_widget_autocomplete`** | kitworks / **[UNKNOWN]** | JS-віджет `kw_autocomplete`, клас `KwAutocompleteField` | `geodata_autocomplete_patch.js:4`, `widget="kw_autocomplete"` у 5 view | Так — `contact, company, crm, hr, lunch` | JS import + monkey-patch + view | Критична (UI) | **Вихідників немає** [UNKNOWN]; monkey-patch `prototype` крихкий (С.12.3) |
| 3 | **`kw_http_request_log`** | kitworks / 16.0.0.5.0 | `kw.http.request.log(.source)` + mixin `kw.http.request.log.source.mixin`; cron очищення | `data/http_request_log_source.xml:3`; **delegate-успадкування** через mixin батька (`http_request_log_source.py:84`) | **Ні (транзитивно через №1)** | Delegate + data-record | Висока | Best-practice nit (Low): додати явно в `depends`, бо geodata прямо посилається на `kw.http.request.log.source`. Auto-створює лог-джерело per-credential; cron-cleanup (С.3.7) |
| 4 | **`kw_mixin`** | kitworks / 16.0 | `use_fname` (`tools.py:6`) — диспетчер `*_geodata`; translit-міксіни | Транзитивно: `use_fname` керує усім `api_request_geodata`/`get_api_headers_geodata`/… | Ні (транзитивно через №3) | Функціональна основа диспетчеризації | **Висока** | Без `use_fname` методи з суфіксом `_geodata` не викликаються; викликає `ensure_one()` |
| 5 | **`generic_mixin`** | crnd-inc / **[UNKNOWN]** | `generic.mixin.transaction.utils` (нова транзакція для логів) | `_inherit` у `kw.api.credential` (`credential.py:16`); `create_in_new_transaction` (`http_request_log.py:153`) | Ні (транзитивно через №3) | Транзакційна утиліта | Висока | Вихідників немає [UNKNOWN]; логи пишуться в окремій транзакції (зберігаються навіть при rollback) |

### 17.2 Зведення для рішень

| Питання | Відповідь |
|---|---|
| Скільки модулів реально потрібно | **5** (усі завантажуються): №1/№2 прямо, №3/№4/№5 транзитивно й функціонально задіяні |
| Що задекларовано коректно | №1, №2 (є в `depends`) |
| Best-practice nit (не блокер) | №3 `kw_http_request_log` — geodata прямо посилається на `kw.http.request.log.source` у data, але не в `depends`. Завантажується транзитивно через №1, тож **не блокує інсталяцію**; додати явно — для коректності |
| Звідки ставити | git: `kitworks-systems/addons` (№1-4) та `crnd-inc/generic-addons` (№5); немає на PyPI |
| Поведінка `api_request` (вирішено) | `timeout=60`, single token-refresh retry, без back-off, `silent`-семантика (`credential.py:87-186`) — див. С.3.8.2 |
| Залишається [UNKNOWN] | вихідники `kw_widget_autocomplete` (JS, `dep_values`) та `generic_mixin` |
| ⚠️ Нова security-знахідка | `api_request` логує `headers` з `Authorization: Bearer {token}` у `kw.http.request.log` (С.7 #15) |
| Найбільший upgrade-ризик | №2 monkey-patch + версійна невідповідність 16.0↔18.0 усіх kw_* (С.12.7) |

---

**Кінець звіту.** Найкритичніше для негайного виправлення: ризики **#1, #2, #3, #4** — без них autocomplete фактично працює лише під адміністратором і тече між компаніями.
