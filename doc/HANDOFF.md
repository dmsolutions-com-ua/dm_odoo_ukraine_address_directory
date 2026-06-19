# HANDOFF — стан проєкту для продовження в новій сесії

> Хендоф-нотатка: що це за проєкт, що зроблено в поточній серії сесій, поточні
> домовленості/конвенції, і що лишилось/заплановано. Дата: 2026-06-11.

## 1. Проєкт

Набір модулів Odoo 19 CE — інтеграція з API **Geodata.online** (автозаповнення,
нормалізація, геокодування, зберігання українських адрес). Усі технічні імена
мають префікс **`dm_`** (модулі) / **`dm.`** (моделі). Шлях:
`c:\work\DM\git\dm-odoo-ukraine-address-directory` (НЕ git-репозиторій).

**Модулі (9):**
- `dm_geodata_connector` — ядро: моделі `dm.geodata.address`,
  `dm.geodata.address.mixin`, `dm.geodata.api.credential`,
  `dm.geodata.request.log`; власний API-клієнт; OWL-віджет `geodata_autocomplete`;
  override `base.geocoder`; безпека/групи; health-моніторинг; мультикомпанія.
- `dm_geodata_online` — парасолькова збірка (meta).
- `dm_geodata_contact` (`res.partner`), `dm_geodata_crm` (`crm.lead`),
  `dm_geodata_company` (`res.company`), `dm_geodata_hr` (`hr.employee` приватна
  адреса), `dm_geodata_bank` (`res.bank`), `dm_geodata_lunch` (`lunch.supplier`) —
  тонкі auto_install-bridge.
- `dm_test_geodata_connector` — тести + mock API.

`lunch.supplier` тримає адресу на `related`-полях до `partner_id` (як
`res.company`), тож на власній формі постачальника поля були б без автопідказки —
`dm_geodata_lunch` додає віджет на цю форму (лише `zip -> zip_code` + related
`country_code`). Auto_install лише коли встановлено й `lunch`, і парасольку.

## 2. Що зроблено в цій серії сесій

1. **Діагностика «не працює автопідказка»**: корінь — не було активного
   `dm.geodata.api.credential` (метод виходив рано, HTTP не йшов). Не баг коду.
2. **Виправлення `res.company`**: бракувало `country_code` → додано
   `country_code = related("country_id.code")` (форма компанії падала).
3. **Health-моніторинг** ([geodata_api_credential.py](../dm_geodata_connector/models/geodata_api_credential.py)):
   `_probe_health`, `_run_health_check`, `_alert_managers`, `action_health_check`
   (кнопка «Check Now»), `_cron_health_check` (щоденний cron
   [data/geodata_health_cron.xml](../dm_geodata_connector/data/geodata_health_cron.xml)).
   Перевірка: доступність сервера, авторизація, баланс (`balance_alert_threshold`),
   наявність credential. Реакція: лог (`WARNING`/`ERROR`) + bus-попап менеджерам
   (`group_geodata_manager`). Поля `health_status/health_message/health_last_check/
   last_balance` + сторінка «Monitoring».
4. **Нові bridge**: `dm_geodata_hr` (override `_geodata_fields` на `private_*`),
   `dm_geodata_bank` (нестандартні m2o `state`/`country`).
5. **Фікс OWL-віджета**: визначення many2one **узагальнено** з метаданих поля
   (`record.fields[key].type`), а не за зашитим списком — щоб ремапнуті поля
   власника (private_state_id, state…) застосовувались на всіх моделях.
6. **Фікс EN-документних адрес**: при ручному пониженні вулиці тепер чистяться й
   EN-поля (`street_en/str_type_en/house_num_add_en`) у
   [geodata_address_mixin.py](../dm_geodata_connector/models/geodata_address_mixin.py)
   `_geodata_sync_on_manual_change` (раніше стара транслітерація лишалась).
7. **Перейменування**: усі 8 модулів → `dm_`, усі 4 моделі → `dm.` (+ усі
   `_inherit`/`env[]`/`ref`/asset-шляхи/OWL-шаблон/`model_*` ext-id/демо/тести).
   Дані не зберігались. Іконки/опис: див. §4.
8. **Мультикомпанія**:
   - `dm.geodata.request.log` отримав `company_id` (+ `ir.rule`) — логи ізольовані.
   - `dm.geodata.address.company_id` дзеркалить компанію власника
     (`_geodata_company_id`; `res.company` override → `self.id`; `res.bank`/без
     `company_id` → глобально). Створення в `apply_address` проставляє компанію.
   - Health-алерти **per-company** (`_alert_managers`/`_cron_health_check` шлють
     менеджерам відповідної компанії; глобальний credential → усім).
9. **Українська локалізація**:
   - **Описи Apps**: переписано багатий [index.html](../dm_geodata_connector/static/description/index.html)
     ядра (плейсхолдери `images/imageN.png` лишаються — зображення замінюються
     вручну) + заповнено 6 порожніх `index.html` бриджів.
   - **Інлайн-коментарі** → українською в усіх `.py` (`#`), `.xml` (`<!-- -->`),
     `.js` (`//`), `.scss`. **Docstrings/JSDoc лишаються англійською.**
   - **`.po`**: `i18n/uk.po` для connector + 5 бриджів + online (meta).
10. **Двомовність форм (фінальний підхід)**: відмовились від хардкоду
    українською у view. Тепер **джерело — англійське**, переклад — через `.po`:
    - У 3 connector-view **прибрано всі `string="..."` на `<field>`** (мітка
      береться з опису поля). Заголовки/кнопки/фільтри/alert — англ. джерело.
    - У моделях кожному показаному полю додано англійське `string=` (щоб мітка
      була з `field_description`, а не auto «Region En»). `help=` — англ. джерело.
    - [dm_geodata_connector/i18n/uk.po](../dm_geodata_connector/i18n/uk.po)
      перегенеровано (**165 записів**, дедупльовано, 0 неперекладених):
      `field_description` усіх полів, `help`, `model_terms` заголовків/кнопок/
      фільтрів, selection, дії/меню, повідомлення, метадані.
11. **CityOld: rename vs старе адмінпідпорядкування**: новий хелпер
    `_city_old_display` у [geodata_address.py](../dm_geodata_connector/models/geodata_address.py)
    показує стару назву населеного пункту лише як **справжнє перейменування** —
    коли `suburb_old` порожнє (`SuburbOld == null`) і `city_old != city`. Якщо
    `suburb_old` заповнене, `CityOld` — старе **адмінпідпорядкування** (не назва)
    і придушується **скрізь**: поле City (`to_address_values`), `{city}`-дужки і
    голий `{city_old}` у документах/конвертах. Тести: 3 нові у
    `test_address_format.py`. UI-рядків/полів не додано → `.po` без змін.
12. **Формати документів/листів + повна EN-транслітерація старих назв**
    ([geodata_address.py](../dm_geodata_connector/models/geodata_address.py),
    [geodata_api_credential.py](../dm_geodata_connector/models/geodata_api_credential.py)):
    - **Нова модель шаблону** (`_render_template`/`_template_values`/`_join_old`,
      `_OLD_PAIRS`): сегменти **через кому**; базовий `{X}` + суміжний `{X_old}`
      → один сегмент `поточне (старе)` (city/street — повний `_city_display`/
      `_street_display(show_old=True)`, тож зі старим типом); самотній `{X}` —
      лише поточне, самотній `{*_old}` — гола стара (мово-залежна).
    - **Gating**: документні/листові адреси (`address_full_*`/`address_letter_*`)
      **завжди зі старим**; `show_old_names` тепер впливає **тільки** на адресний
      блок партнера (`to_address_values`).
    - **Дефолт**: `_DEFAULT_ADDRESS_FORMAT` для `address_format_document/letter`
      (раніше порожні). Лист тепер теж із `{country}` (за вказівкою).
    - **Перевірка дублів** у `_check_address_format`; `{hromada_old}` додано до
      дозволених плейсхолдерів.
    - **Нові колонки** `region_old_en/_ru`, `hromada_old_en/_ru`,
      `settlement_type_old_en/_ru` + інгестія + `_EN_API_KEYS` (раніше 4 із 7
      старих EN-полів) → EN-адреса повністю транслітерована. EN-вкладка форми
      «Адреса Geodata» показує старі назви. Тести в `test_address_format.py`
      оновлено/додано (default, пари, дублі, hromada_old, EN-translit, gating).
13. **UI-правки адресного блоку, форм і переклади**:
    - **Детермінований порядок** полів адреси (Місто, Область, Район, Громада,
      Індекс, Країна): на `div.o_address_format` у bridge-формах (contact 2 форми,
      crm, company) додано клас `o_geodata_address_grid`; SCSS робить його
      `display:flex` з явними `order` (не залежить від inline-block переносу теми).
      У contact звужено unscoped xpath area/hromada до `o_address_format`. HR —
      звичайний group (порядок за DOM, без класу).
    - **Вкладка** «Address Information» → UA «Інформація про адресу» (msgstr у
      contact/crm/hr `uk.po`; EN-джерело без змін).
    - **EN-адреса завжди видима** на формі контакту (прибрано
      `invisible="not geodata_address_*_en"`); вміст усе одно за `store_english`.
    - **EN-поля старих назв** отримали `string=` (7 шт.) → перекладено в connector
      `uk.po`; додано переклади міток `Current`/`Old names`, `write_date`
      («Останнє оновлення»).
    - **Технічні підказки налаштувань** (3 alert-блоки) перекладено: точні
      `model_terms`-референси згенеровано через `odoo.tools.translate.xml_translate`
      (Odoo встановлено локально), тож вони гарантовано застосовуються.
    - **Країна праворуч від Індексу**: country у grid-SCSS отримав
      `flex: 1 1 50%` (замість повного рядка) → zip+country на одному рядку (UA);
      для не-UA коректно переноситься. Web-рендерер `o_address_format` сам
      переставляє стандартні поля, тож порядок керується ВИКЛЮЧНО CSS-`order`;
      country покрито і прямо, і через обгортку `partner_address_country` (`:has`).
    - **Суфікс громади** `_hromada_suffix` (`geodata_address.py`): API дає громаду
      голою (region/area вже з «обл.»/«р-н»), тож на відображенні додаємо «гр.»
      (UA) / «gr.» (EN) — у `to_address_values` і `_template_values` (поточна й
      стара). Збережене значення лишається голим. Тести в `test_address_format.py`
      оновлено.
14. **Bugfix: розсинхрон UA/EN адрес** (`fetch_en_translit`). Симптом: після
    кількох змін адреси на одній картці вкладка «Інформація про адресу» показувала
    РІЗНІ UA та EN адреси, і пересейв не лікував. Причина: EN-поля `_en`
    оновлювались окремим (повторним нечітким) HTTP-запитом і лише ДОПИСУВАЛИСЬ —
    відсутні у відповіді поля та порожня/невдала відповідь лишали `_en` від
    ПОПЕРЕДНЬОЇ адреси; `address_full_en` (stored compute) перераховувався з
    застарілих `_en`, тож пересейв не допомагав. Фікс: `fetch_en_translit` тепер
    **щоразу перезаписує ВЕСЬ набір `_en`** (відсутні ключі → `False`); порожня
    відповідь → усі `_en` чистяться, EN падає на UA-fallback (та сама адреса), а не
    лишається на старій. Тести: `test_translit_consistency.py` (omit-field,
    empty-response, end-to-end consistency).
15. **Bugfix: «прилипання» старих назв на перевикористаному записі**
    (`update_from_api`). Симптом: на одній картці після адреси з old-назвою вибір
    іншого міста (напр. Харків, без old) проставляв стару назву від попередньої
    адреси — так само район/громада. Причина — той самий клас, що §14:
    `_api_data_to_vals` відкидає `None`, а settlement-рівневі `*_old` не
    скидались. Фікс: **рівневий ресет** у `update_from_api` — payload, що несе
    ідентичність рівня (`City`/`Street`/`HouseNum|HouseId`), скидає опційні поля
    цього рівня (`_SETTLEMENT_RESET`/`_STREET_RESET`/`_HOUSE_RESET`), відсутні
    ключі → `False`. Працює і для повної адреси (level=house раніше не чистив
    settlement-old). `*_old_en` уже чистить §14. Тести: `test_old_names_reset.py`.
16. **Перемикач `show_old_names` перейменовано** (мітка): «Show historical (old)
    names» → «**Store** historical (old) names» / UA «**Зберігати** історичні
    (старі) назви» — призначення: чи зберігати старі назви в полях City/Street
    адресного блоку (у документах/листах вони завжди). Технічне ім'я поля
    лишилось `show_old_names`. Оновлено `string`/`help`, connector `uk.po`
    (field_description + help) і alert «Address Formats» (новий `model_terms`
    перегенеровано через `xml_translate`).
17. **Bugfix: жива перевірка ручної зміни поля Street** (`_compute_geodata_verified`).
    Симптом: вибір вулиці зі списку → ручна зміна назви → підсвічування «введено
    вручну» не з'являлось до збереження. Причина: `geodata_street_verified =
    bool(street_ref)`, а street не в `_GEO_DETACH_LEVELS` (на відміну від міста),
    тож `street_ref` знижувався лише на save; до того ж compute не залежав від поля
    вулиці власника. Фікс: `_compute_geodata_verified` тепер **порівняльний** —
    вулиця підтверджена лише якщо `street_ref` встановлено **і** значення поля
    власника не розійшлося з валідованим (з винятком house-only через
    `_is_house_only_change` — та сама логіка, що й на save), а `@api.depends`
    зроблено **динамічним** (lambda) із полем вулиці власника
    (`self._geodata_fields["street"]`) → правка тригерить перерахунок наживо.
    Тест: `test_address_sync.py::test_street_manual_change_unverifies_live`.
18. **Перфоманс/налаштування автопідказки** (ціль — **дохід за виклик**; модуль
    розробляє власник платного API):
    - **Кеш міст ПРИБРАНО** (`_CITY_CACHE`/`import time`) — кожен реальний пошук
      іде в API. Налаштування **«Server cache TTL (s)»** (`cache_ttl_s`) видалено
      (модель/view/`uk.po`).
    - **Реюз монікера (15 хв):** нові поля `dm.geodata.address.city_moniker_ts`/
      `street_moniker_ts`; `geodata_autocomplete_streets` бере монікер зі
      **збереженого** запису, поки свіжий (`_MONIKER_TTL=15хв`, `_moniker_fresh`),
      і ре-резолвить через API Cities лише коли немає/застарів/API «expired». Це
      усуває зайвий повторний API Cities при наборі вулиці (транзитивне dep-поле
      губилось на round-trip'ах → форсувало ре-резолв). dep лишився запасним хінтом.
    - **«Мінімум символів» ≥ 3** — `@api.constrains("min_chars")`.
    - **Debounce = 250 мс** — дефолт віджета `|| 300`→`|| 250` (реально діюче),
      `credential.debounce_ms` default→250. *Поле наразі не «прокидається» у віджет
      (в'ю шлють лише `min_chars`) — діє дефолт віджета.*
    - **Commit лише на select/blur** — `onInput` більше не комітить значення
      щокнопки (зник per-keystroke onchange-RPC); `_commitNow` на blur + apply на
      select достатньо.
    - **`_compute_geodata_verified` полегшено** — credential читається ОДИН раз
      (не `get_credential()`/`to_address_values()` на кожен запис); валідована
      вулиця рахується напряму через `_street_display`+`_house_part`.
    - Тести: `test_perf_settings.py` (моникер-реюз fresh/stale, ts на інгесті,
      min_chars<3 → ValidationError).
    - **Memory:** збережено факт «модуль розробляє власник платного API → дохід за
      виклик; кешування не додавати».

## 3. Поточні конвенції (дотримуватись далі)

- **UI-текст** (мітки полів, повідомлення `_()`, рядки view, назви/summary): у
  **джерелі англійською**, переклад — у `i18n/uk.po`. **НЕ хардкодити українську
  у view/моделях.** Мітки полів — лише через модельне `string=` (як `hromada`),
  без `string`-перевизначень у view.
- **Коментарі в коді**: українською (інлайн). Docstrings/JSDoc — англійською.
- **Текст поза кодом** (чат, MD): українською. Технічні токени (`sudo`, `bus`,
  `Bearer`, назви полів/моделей, `AUDIT #N`) — як є.
- **Моделі/поля** не перейменовувати без потреби; field-імена `geodata_*`
  лишаються (вони не модуль/модель).
- **Провайдер геокодера** `base.geo_provider` `tech_name=geodata` і реєстрове
  ім'я віджета `geodata_autocomplete` — НЕ чіпати.

## 4. Що лишилось / заплановано

1. ~~**Alert-блоки на формі облікових даних (3 шт.)** не перекладені~~ —
   **ВИРІШЕНО** (серія §2.13): додано до `uk.po`. Точні `model_terms`-референси
   згенеровано через `odoo.tools.translate.xml_translate` (а не ручні),
   тож застосовуються гарантовано. При зміні тексту alert — оновити відповідний
   `msgid` тим самим способом.
2. **Bridge-форми** (`dm_geodata_*/views/*.xml`, сторінка «Address Information»)
   досі мають `string="..."`-перевизначення полів (KATOTTG, KOATUU, Document(UA),
   placeholder-и…), що перекладаються через `model_terms` у bridge `uk.po`.
   **План**: застосувати той самий принцип, що й до connector — прибрати
   `string`-перевизначення з view, спертись на `field_description` (поля міксина,
   матеріалізовані на власнику → `field_<owner>__<field>` у bridge `uk.po`).
3. **Фінальна звірка `.po`-референсів**: офлайн будувались за конвенціями Odoo.
   Рекомендовано один раз `odoo-bin --i18n-export -l uk_UA` на встановленій БД і
   звірити/доповнити (записи з невірним референсом просто не застосуються —
   інсталяцію не ламають).
4. **Зображення Apps**: `dm_geodata_connector/static/description/images/imageN.png`
   — користувач замінює вручну; `index.html` уже посилається на розумний набір.
5. **BLUEPRINT (§2.1)** згадує неіснуючу модель `geodata.api.client` — за бажання
   привести до `dm.*` / прибрати (косметика документа).
6. **Опційно**: `geodata_bank` зроблено; `geodata_lunch` зроблено (bridge на
   `lunch.supplier`, related-поля до партнера, як company).

## 5. Перевірка / запуск (на боці користувача — Odoo тут не запускається)

```
# встановити весь набір
odoo-bin -d <db> -i dm_geodata_online --stop-after-init
# оновити ядро + підвантажити українську
odoo-bin -d <db> -u dm_geodata_connector -l uk_UA --i18n-overwrite --stop-after-init
# тести
odoo-bin -d <db> -i dm_test_geodata_connector --test-enable --stop-after-init
```

**Офлайн-валідація (доступна тут):**
- `ast.parse` усіх `.py`; `xml.dom.minidom` усіх `.xml`; `polib` усіх `.po`
  (перевірити: без дублів msgid, без неперекладених). Усе наразі **проходить**.
- Перемкнути мову EN↔UK на формі «Детально про адресу» (усі вкладки), формі
  облікових даних, журналі запитів: під EN — англ., під UK — укр., без хардкоду.

## 6. Корисні точки в коді

- Загальна логіка адрес: [geodata_address_mixin.py](../dm_geodata_connector/models/geodata_address_mixin.py)
  (`apply_address`, `_geodata_onchange`, `_geodata_sync_on_manual_change`,
  `_geodata_company_id`, `geodata_autocomplete_cities/streets/full_address`).
- Сховище/формати адрес, інгестія, EN-транслітерація:
  [geodata_address.py](../dm_geodata_connector/models/geodata_address.py).
- API-клієнт, токен, логування, health, payment(402):
  [geodata_api_credential.py](../dm_geodata_connector/models/geodata_api_credential.py).
- OWL-віджет: [static/src/js/geodata_autocomplete_field.js](../dm_geodata_connector/static/src/js/geodata_autocomplete_field.js).
- Патерн bridge: [dm_geodata_crm/models/crm_lead.py](../dm_geodata_crm/models/crm_lead.py)
  (стандартні імена) та [dm_geodata_bank/models/res_bank.py](../dm_geodata_bank/models/res_bank.py)
  (нестандартні m2o) + `views/*.xml`.
- Документація: per-module `README.md`, кореневий `README.md`,
  [BLUEPRINT_GeodataUkraine_v1.0.md](BLUEPRINT_GeodataUkraine_v1.0.md), `AUDIT.md`.
