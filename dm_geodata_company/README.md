# Ukraine Address Integration - Companies (dm_geodata_company)

Adds Geodata.online address autocomplete to the **company** form
(Settings → Companies).

- `res.company` inherits `dm.geodata.address.mixin` (standard address field names).
- City / Street use the `geodata_autocomplete` widget; District (`area`) and
  Hromada are auto-filled (shown per the credential toggles); gated on country =
  Ukraine via a `country_code` related field this module adds (`res.company` has
  none of its own: `country_code = related="country_id.code"`, like `crm.lead`).

Note: a company's address fields are `compute/inverse` to its `partner_id`, so
the address text is shared with the company's contact, while the Geodata link is
the company's own (1:1 per owner).

Packaging: this is an **auto_install bridge** depending on `dm_geodata_online` —
installing the umbrella attaches it, uninstalling the umbrella removes it.
