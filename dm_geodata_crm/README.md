# Ukraine Address Integration - CRM (dm_geodata_crm)

Adds Geodata.online address autocomplete to **crm.lead** (leads / opportunities).

- `crm.lead` inherits `dm.geodata.address.mixin` (standard address field names, so
  no `_geodata_fields` override is needed).
- City / Street use the `geodata_autocomplete` widget; District (`area`) and
  Hromada are auto-filled (shown per the credential toggles).
- An **Address Information** page shows the one-line search and the document /
  letter addresses. Everything is gated on country = Ukraine via a `country_code`
  related field this module adds (`crm.lead` has none of its own).

Thin integration — all the logic lives in the mixin; this module only declares
the inherit, the `country_code` related field, onchange wrappers and view.

Packaging: this is an **auto_install bridge** depending on `dm_geodata_online` and
`crm` — it attaches automatically when both are installed, and is removed when
`dm_geodata_online` is uninstalled.
