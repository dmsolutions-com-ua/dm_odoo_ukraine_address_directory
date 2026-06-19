# Ukraine Address Integration - HR (dm_geodata_hr)

Adds Geodata.online address autocomplete to the **employee private (home) address**
(`hr.employee`, *Private Information* tab).

- `hr.employee` inherits `dm.geodata.address.mixin`. The employee keeps its home
  address on its own `private_*` columns (no `res.partner` delegation in Odoo 19),
  so the module overrides `_geodata_fields` to map the logical address levels onto
  those names:
  `country_id → private_country_id`, `state_id → private_state_id`,
  `city → private_city`, `street → private_street`, `street2 → private_street2`,
  `zip → private_zip` (`area`/`hromada` are the mixin's own fields).
- City / Street use the `geodata_autocomplete` widget; District (`area`) and
  Hromada are auto-filled (shown per the credential toggles). Everything is gated
  on country = Ukraine via a `country_code` related field this module adds
  (`hr.employee` has none of its own: `related="private_country_id.code"`).
- An **Address Information** page shows the one-line search and the document /
  letter addresses.

Thin integration — all the logic lives in the mixin; this module only declares
the inherit, the `_geodata_fields` map, the `country_code` related field, the
onchange wrappers and the view.

Packaging: this is an **auto_install bridge** depending on `dm_geodata_online` and
`hr` — it attaches automatically when both are installed, and is removed when
`dm_geodata_online` is uninstalled.
