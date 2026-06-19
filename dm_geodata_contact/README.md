# Ukraine Address Integration - Contacts (dm_geodata_contact)

Adds inline Geodata.online address autocomplete to **res.partner** (Odoo 19 CE).

- City / Street fields use the `geodata_autocomplete` widget from
  `dm_geodata_connector` (debounce, min_chars, keyboard nav, themed content-width
  dropdown).
- District (`area`) and Hromada are read-only and auto-filled from the selected
  address. In the form they sit **side by side** in the address block (like
  City/State — `display:inline-block` under `.o_form_editable .o_address_format`)
  and wrap responsively when the window narrows. Their display is controlled by
  the credential toggles **Show District/Raion field** / **Show Hromada field**
  (both **off by default** — the values are still filled and used in document
  addresses, only the form fields are hidden).
- An **Address Information** page shows the validated document/letter
  addresses (UA/EN) and KATOTTG/KOATUU codes (no `Ids`/`Full Address`/`Reset`
  buttons; open the full record via the `Geodata Address` field link).
- **No wizard.** Address entry is inline only.
- Works on the main contact form **and** on the child-address dialog
  (Delivery / Invoice / Other addresses). The Contacts &amp; Addresses dialog is
  the **inline form inside `child_ids`** of `base.view_partner_form` (scoped via
  `//field[@name='child_ids']//div[@name='div_address']`); the standalone
  `base.view_partner_address_form` is also extended for flows that use it. In the
  compact dialog only the **autocomplete** (city/street/house) and the
  Район/Громада fields are added — the one-line search and the document/letter
  details stay on the main form's **Address Information** tab (to keep the dialog
  layout intact).
- **Strict 1:1 ownership:** each partner has its own private `dm.geodata.address`
  row — no deduplication, no sharing. Detaching the link or deleting the partner
  removes that orphan row.
- Verified-only model (v1.5): editing or clearing the settlement (or a level
  above it — state/district/hromada) so it no longer matches the validated
  address **detaches** the Geodata link and clears the dependent address block
  immediately in the form (before save). Editing the street only **downgrades**
  the verification level (street/house), keeping the settlement validated.
- `action_geodata_reset` still exists programmatically (used by tests) to fully
  detach the validated address, though the form no longer exposes a button.
