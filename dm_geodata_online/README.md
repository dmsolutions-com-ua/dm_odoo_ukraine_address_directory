# Reference Directory of Ukrainian Addresses (dm_geodata_online)

**Umbrella application** for the Odoo App Store. **Empty** (no own models/views)
— it is the single install/uninstall switch for the suite.

Depends: `dm_geodata_connector` (the engine).

Behaviour:
- **Install** `dm_geodata_online` → installs the core; the **auto_install bridges**
  attach where their app is present: `dm_geodata_contact` (Contacts),
  `dm_geodata_crm` (CRM), `dm_geodata_company` (companies).
- **Uninstall** `dm_geodata_online` → cascades to those bridges (they depend on it).
  The core `dm_geodata_connector` stays installed — uninstall it separately to fully
  remove everything.
