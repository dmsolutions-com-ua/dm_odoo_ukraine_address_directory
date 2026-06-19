# Ukraine Address Integration - Banks (dm_geodata_bank)

Adds Geodata.online address autocomplete to the **bank** form
(`res.bank`; Contacts → Configuration → Banks, or Accounting → Banks).

- `res.bank` inherits `dm.geodata.address.mixin`. The bank carries its own address
  columns but uses the **non-standard** many2one names `state`/`country` (not
  `state_id`/`country_id`), so the module overrides `_geodata_fields` to map the
  logical levels onto them (`state_id → state`, `country_id → country`; the rest
  are standard: `city`/`street`/`street2`/`zip`; `area`/`hromada` are the mixin's
  own fields).
- City / Street use the `geodata_autocomplete` widget; District (`area`) and
  Hromada are auto-filled (shown per the credential toggles). Everything is gated
  on country = Ukraine via a `country_code` related field this module adds
  (`res.bank` has none of its own: `related="country.code"`).
- A one-line address search and the document / letter addresses are shown below
  the address block.

Thin integration — all the logic lives in the mixin; this module only declares
the inherit, the `_geodata_fields` map, the `country_code` related field, the
onchange wrappers and the view.

Packaging: this is an **auto_install bridge** depending on `dm_geodata_online`
(`res.bank` lives in `base`, always present) — installing the umbrella attaches
it, uninstalling the umbrella removes it.
