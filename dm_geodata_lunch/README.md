# Ukraine Address Integration - Lunch (dm_geodata_lunch)

Adds Geodata.online address autocomplete to the **lunch supplier** form
(Lunch → Configuration / Vendors).

- `lunch.supplier` inherits `dm.geodata.address.mixin`. Its address fields are
  `related` (with inverse) to `partner_id`, just like `res.company`, so the
  address text is shared with the supplier's contact while the Geodata link is
  the supplier's own (1:1 per owner).
- City / Street use the `geodata_autocomplete` widget; District (`area`) and
  Hromada are auto-filled; gated on country = Ukraine via a `country_code`
  related field this module adds (`lunch.supplier` has none of its own).
- The supplier's zip field is named `zip_code` (related to `partner.zip`), so the
  module remaps `_geodata_fields["zip"] -> "zip_code"`; everything else uses the
  mixin's standard field names.

Packaging: this is an **auto_install bridge** depending on `dm_geodata_online`
and `lunch` — it attaches only when both the umbrella and the Lunch app are
installed, and is removed when either is uninstalled.
