# Ukraine Address Reference Directory (dm_geodata_connector)

Core module: self-contained integration with the **Geodata.online** API for
Ukrainian address autocomplete, normalization and geocoding (Odoo 19 CE).

## What it provides
- `dm.geodata.address` — normalized address storage (UA + EN), document/letter
  formats, KATOTTG/KOATUU codes, coordinates.
- `dm.geodata.address.mixin` — abstract mixin with autocomplete entry points, the
  `apply_address` sudo service, the `area`/`hromada` fields and **all** the
  owner-side logic (clear-down, detach/downgrade, verification, write-sync,
  1:1 orphan GC) — field-name-agnostic via `_geodata_fields`, so it works on any
  model that carries an address.
- `dm.geodata.api.credential` — **own** API client (no external `kw_*`): token
  refresh, 60s timeout, single 401-retry, masked request logging.
- `dm.geodata.request.log` — masked HTTP log (Authorization never stored in
  clear text) with a daily cleanup cron.
- `base.geocoder` override — geocoding provider without side-effect record
  creation.
- `geodata_autocomplete` — own OWL field widget (debounce, min_chars,
  skip-on-space/dedup). The text input is **uncontrolled**: the typed value is
  committed to the record on a short debounce / on blur (not per keystroke), so
  fast typing never loses characters and the server onchange is not fired on
  every letter. When a suggestion is picked, the applied value is written into
  the input explicitly at the end of selection, so it survives a following blur
  (it is not re-committed or cleared on focus loss). The suggestion list uses the
  standard Bootstrap **`dropdown-menu`/`dropdown-item`** chrome (no hardcoded
  colors) and is sized to its **content** (the longest label), independent of the
  field width (`width: max-content`, capped by `max-width`); near the right screen
  edge it is right-anchored so it never overflows the viewport. Keyboard
  navigation (↑/↓/Enter/Escape) works while the **field keeps focus** (ARIA
  combobox/listbox); the active/hover item is highlighted with the same Sass
  dropdown colors the core autocomplete uses (`$dropdown-link-hover-color/-bg`) —
  Odoo does not emit the Bootstrap `--bs-dropdown-*` CSS variables, so a CSS-var
  approach would render no highlight. After a suggestion is picked, focus returns
  to the field with the caret at the end so typing can continue
  (city → street → house). The list closes on Escape, on selection, and on a
  pointer-down anywhere outside the widget (not only on input blur).

## Design notes (vs the previous version's audit)
- No external `kw_api_connector` / `kw_widget_autocomplete` / `generic_mixin`.
- No wizard. Address entry is inline autocomplete only.
- UA + EN only (no Russian fetched).
- **Stores everything the API returns, without exceptions.** The UA ingestion
  (`_api_data_to_vals`) maps every documented field; the EN transliteration
  (`fetch_en_translit`, driven by `_EN_API_KEYS`) captures **all** `_en` columns
  — including the house-number suffix (`house_num_add_en`), settlement district
  and old names — not a hand-picked few. A raw `api_payload` (`fields.Json`)
  additionally keeps each response verbatim per language (`"ua"`/`"en"`, merged
  across the city→street→house chain), so even new/undocumented keys are never
  lost. The EN document address transliterates the house suffix too
  (`вул. Механізаторів, 14Д` → `vul. Mekhanizatoriv, 14d`).
- No HTTP inside `create()`/compute; ingestion happens only on selection.
- Access token stored in `ir.config_parameter`; never logged.
- Multi-company record rules on address and credential.

## Configuration
Settings → Geodata.online → API Credentials → enter username/password →
**Test Connection** (verifies + syncs Ukraine oblasts).

## Security of the paid account credentials
The Geodata.online login/password are protected against leakage:
- The **API Credentials** menu is visible to *Geodata.online Manager* only.
- `dm.geodata.api.credential` is readable/writable by managers only (no read for the
  plain *Geodata.online User* group).
- `api_username` / `api_password` carry `groups="base.group_system"`, so the ORM
  exposes them **only to Settings administrators** — they cannot be read via RPC,
  export or the form by plain users or non-system managers. Server flows read them
  via `sudo()` (`_refresh_token`), so autocomplete and **Test Connection** keep
  working without revealing the secrets. The access token lives in
  `ir.config_parameter` (sudo) and request logs mask the `Authorization` header.
- Consequence: a **Settings administrator** sets/edits the username & password;
  managers configure the non-secret settings (formats, logging, languages).

> Future hardening (optional): move `api_password` itself into
> `ir.config_parameter` as a write-only field (like the token).

## Address ownership (strict 1:1)
Every owner (a `res.partner`, or any record using `dm.geodata.address.mixin`) has
its **own private** `dm.geodata.address` row. There is **no deduplication and no
sharing**: each new selection for an owner without a linked address **creates**
a fresh row (`create_from_api`), and two entities at the same physical address
each keep their own row. When the owner drops the link (**Reset Geodata** or a
manual settlement change) or is deleted, its now-orphan private row is
**deleted** (centralised in the mixin's `write`/`unlink`). The progressive
city→street→house chain keeps mutating that one owned row (`update_from_api`).

## Address consistency (verified-only)
`dm.geodata.address` stores only **verified** levels (those chosen from the
directory; detected via `settlement_ref`/`street_ref`/`house_ref`). Manually
typed values that are not in the directory stay only on the partner's address
block. Selecting a higher level clears the lower ones (clear-down); a manual
edit downgrades the verified level (street) or detaches the link (settlement/
oblast). Document/letter addresses reflect only the verified part (the
`geodata_verified_level` is computed but not shown on the partner form).
Manually-entered, non-empty address fields are marked with a single **amber
info icon** with a tooltip — **only for Ukrainian addresses** (country = UA),
since the module handles UA addresses only (no border; toggle: credential
**Highlight manual address data**). Expired search monikers are re-resolved
automatically (no buttons).

## Historical (old) names
"Old" covers **both the name and the type**. The parentheses placement depends on
what changed: an old **name** goes at the **end**
(`вул. Стуса Василя (вул. Механізаторська)`); when **only the type** changed it
goes **right after the current type**, before the name (`селище (смт) Іваничі`).

**Where old names are shown — two different rules:**

- **Contact address block** (`res.partner.city/street/area/hromada`,
  `to_address_values`) is gated by the credential toggle **Store historical (old)
  names** (`show_old_names`, default off): on → current name with the old one in
  parentheses stored in the City/Street/District/Hromada fields; off → current
  only.
- **Document / letter addresses** on the Geodata Address form
  (`address_full_*`, `address_letter_*`) **always** show old names/types,
  regardless of `show_old_names`.

**Template model (document/letter).** A template is an ordered list of
placeholders; non-empty segments are joined with **commas**. Base placeholders
`{region}/{area}/{hromada}/{city}/{street}` render the **current** value only. A
base placeholder immediately followed by its `{*_old}` counterpart is **merged**
into one `current (old)` segment — for `city`/`street` this also carries the old
type (`село (смт) Іванівське`, `вул. Центральна (Леніна)`). A standalone
`{*_old}` renders the bare old name (language-aware, transliterated in EN). Each
placeholder may be used only once. Both format fields ship with a sensible
**default** template (see `_DEFAULT_ADDRESS_FORMAT`).

For the **settlement** there is an extra rule (`_city_old_display`): `CityOld`
is shown only when it is a **genuine rename** — when there is no old suburb
(`SuburbOld` empty) and it differs from the current name. When `SuburbOld` is
present, `CityOld` reflects an old **administrative subordination** (not a
rename) and is suppressed everywhere — in the City field, in the `{city}`
parentheses and in the bare `{city_old}` placeholder.

Full **EN transliteration** of old names requires the `*_old_en` columns
(`region_old_en`, `area_old_en`, `hromada_old_en`, `settlement_type_old_en`,
`city_old_en`, `str_type_old_en`, `street_old_en`), captured from the API by
`_EN_API_KEYS` / `fetch_en_translit`. On the contact form the **EN** document /
letter address fields are **always shown** (their content is still governed by
*Store English Transliteration*).

## Address block field order
Odoo's web renderer rearranges the standard `.o_address_format` fields by the
country address format and appends injected fields (District/Hromada) after them,
and the inline-block widths wrap unpredictably. The bridge views add the class
**`o_geodata_address_grid`** to `div.o_address_format`; the connector SCSS turns
it into a flexbox with explicit `order` so the order is deterministic —
**City, Region/Oblast, District, Hromada, ZIP | Country** (Country sits to the
right of ZIP) — regardless of theme. The country `order` targets both the direct
field and the `partner_address_country` wrapper (via `:has`). `hr.employee` uses
a plain group (DOM order), so it needs no class.

## Hromada suffix
The API returns the hromada **bare** (unlike region/area, which already carry
`обл.`/`р-н`). At display time the connector appends the abbreviation —
**`гр.`** (UA) / **`gr.`** (EN) — to the hromada in the partner address block
(`to_address_values`) and in the document/letter addresses (`_template_values`),
e.g. `Берестинська гр.` / `Berestynska gr.`. The stored
`dm.geodata.address.hromada` stays bare (`_hromada_suffix` is display-only).

Because the editable City/Street
inputs may now carry the `(old name)`, the autocomplete (city/street/house
search) and the manual-edit verification **strip the `(...)` part**
(`_strip_old_paren`), exactly like the street type is stripped — so toggling the
setting never breaks search and never looks like a manual edit.

## Reusing on other models
Any model that carries an address can get the same behaviour by inheriting
`dm.geodata.address.mixin` (the owner-side logic is field-name-agnostic). Recipe
for a thin integration module:

1. **Model**: `_inherit = ["<your.model>", "dm.geodata.address.mixin"]`. If the
   address fields are **not** the standard names, override the map, e.g.
   `_geodata_fields = {"city": "private_city", "street": "private_street",
   "state_id": "private_state_id", "zip": "private_zip",
   "country_id": "private_country_id", "street2": "private_street2",
   "area": "area", "hromada": "hromada"}`. Standard-named models
   (e.g. `crm.lead`) need no map.
2. **Onchange wrappers** (the mixin can't hardcode field names): declare
   `@api.onchange(<real field>)` methods calling `self._geodata_onchange(level)`
   for the levels you want live clear-down (`state_id`/`area`/`city`/`street`).
3. **View**: put `widget="geodata_autocomplete"` on the city/street fields (with
   the same `options` as the contact form), add the hidden control fields
   (`geodata_address_id`, monikers, `country_code`, verified flags…) and the
   **Address Information** page. `res.partner` (`dm_geodata_contact`) is the
   reference implementation.

Ready examples of such thin modules: **`dm_geodata_crm`** (`crm.lead`, standard
field names), **`dm_geodata_company`** (`res.company`), **`dm_geodata_hr`**
(`hr.employee`, private `private_*` fields → `_geodata_fields` override) and
**`dm_geodata_bank`** (`res.bank`, non-standard m2o `state`/`country` → override).
The UA view gate uses the model's own `country_code` field; models that lack one
(`crm.lead`, `hr.employee`, `res.bank`) add it as a related field, e.g.
`country_code = related="country_id.code"` (or `private_country_id.code` /
`country.code`). The widget applies returned many2one values by detecting the
field type from the record metadata (not a fixed name list), so remapped owner
fields like `private_state_id` or `state` are set correctly.

`lunch.supplier` exposes its address as `related` fields to its `partner_id`
(like `res.company`), so its own form would otherwise have plain text fields with
no autocomplete — `dm_geodata_lunch` adds the widget on the supplier form itself
(it only remaps `zip -> zip_code` and adds a `country_code` related field). Other
models that merely embed a `partner_id` (e.g. `sale.order`, editing the partner
inline) are covered by `dm_geodata_contact`; `res.company` likewise proxies to its
partner but gets its own bridge `dm_geodata_company`.

## Request Log
Settings → Geodata.online → **Request Log** (manager-only) lists every API
call (`dm.geodata.request.log`): URL, method, HTTP status, duration, params and
headers (with the Authorization token masked). Each entry carries a `company_id`
(the credential's company, or the acting company for a global credential) and a
multi-company `ir.rule`, so a manager sees only their own company's logs. Entries
are auto-purged by the daily cleanup cron after `log_retention_days`.

## Health monitoring
Because a misconfiguration is silent (no active credential → autocomplete simply
does nothing, and no API call is even attempted), the credential is **proactively
checked**, so an admin reacts early instead of by accident.

- **What is checked** (`_probe_health` / `api/Account/UserInfo`): server
  reachability, authentication validity and the **account balance** (against
  `balance_alert_threshold`). The cron also flags, **per company**, any company
  for which no active credential resolves (`get_credential(company)`).
- **How it runs**: a daily scheduled action **Geodata: health check**
  (`_cron_health_check`) plus a **Check Now** button on the credential form
  (`action_health_check`).
- **Reaction**: every problem is written to the server log
  (`WARNING`/`ERROR`) **and** pushed to *Geodata.online Manager* users as a live
  popup (`bus.bus` notification, throttled by `payment_notification_interval`).
  Alerts are **company-scoped**: a company-specific credential notifies only that
  company's managers; a global credential notifies all of them. This complements
  the reactive HTTP-402 *insufficient funds* notification.
- **Where you see it**: the **Monitoring** page (settings:
  `health_check_enabled`, `balance_alert_threshold`, alert interval) and a
  read-only **Status** block / list badge: `health_status`
  (OK / Warning / Error / Not checked), `last_balance`, `health_last_check`,
  `health_message`.

## Multi-company
Isolation follows company boundaries throughout:
- **Credentials** — `get_credential(company)` prefers the active credential of the
  current company and falls back to a global one (`company_id` empty). So you can
  run one shared Geodata account or a separate account (and balance/billing) per
  company. Secrets stay `base.group_system`-only regardless of company; the access
  token is stored per credential id.
- **Addresses** — `dm.geodata.address` is scoped to its owner's company
  (`_geodata_company_id`): a company-specific owner → its company; a
  multi-company-shared owner (`company_id` empty) → a shared address; `res.company`
  → itself. A multi-company `ir.rule` (global + `company_ids`) enforces visibility.
- **Request log** — per-company (see above).
- **Health alerts** — per-company (see above).
