# dm-odoo-ukraine-address-directory (Odoo 19 CE)

Self-contained integration with the **Geodata.online** API for Ukrainian
address autocomplete, normalization and geocoding. Rebuilt from scratch on
Odoo 19 from the forensic audit of the previous version
(`doc/AUDIT.md`) per `doc/BLUEPRINT_GeodataUkraine_v1.0.md`.

## Modules
| Module | Role |
|--------|------|
| `dm_geodata_connector` | Core: address model, own API client, own OWL autocomplete widget, geocoder, security, health monitoring |
| `dm_geodata_contact` | Inline autocomplete on `res.partner` (no wizard) |
| `dm_geodata_crm` | Inline autocomplete on `crm.lead` (auto-install bridge) |
| `dm_geodata_company` | Inline autocomplete on `res.company` (auto-install bridge) |
| `dm_geodata_hr` | Inline autocomplete on the `hr.employee` private address (auto-install bridge) |
| `dm_geodata_bank` | Inline autocomplete on `res.bank` (auto-install bridge) |
| `dm_geodata_lunch` | Inline autocomplete on `lunch.supplier` (auto-install bridge; needs `lunch`) |
| `dm_geodata_online` | Empty meta-bundle (installs the set) |
| `dm_test_geodata_connector` | Mock API + unit tests (test DBs only) |

> `lunch.supplier` exposes its address as `related` fields to its `partner_id`
> (like `res.company`), so its own form has plain text fields with no
> autocomplete — `dm_geodata_lunch` adds the widget on the supplier form itself.
> All bridges are thin: they reuse `dm.geodata.address.mixin`.

## Key design decisions
- **Self-contained** — no `kw_*` / `generic_mixin` dependencies.
- **No wizard** — address entry is inline autocomplete only.
- **UA + EN** address languages (no Russian).
- **Sync + debounce/dedup/cache** — client debounce 300 ms, `min_chars`,
  skip-on-space; server normalizes & dedups before any (billed) API call.
- **Field-name-agnostic mixin** — one `dm.geodata.address.mixin` drives every
  owner model; a bridge only maps `_geodata_fields` and adds the view.
- **Proactive health monitoring** — a daily cron + a manual button verify
  server reachability, authentication, balance and credential presence, and
  alert *Geodata.online Manager* users via the server log and a live popup.
- **Multi-company isolation** — credentials resolve per-company (or global);
  addresses are scoped to their owner's company; request logs and health alerts
  are company-scoped via `ir.rule` and recipient filtering.

## How the audit defects were addressed
See the full mapping in `doc/BLUEPRINT_GeodataUkraine_v1.0.md` §7.1. Highlights:
token kept out of the DB table and masked in logs; multi-company record
rules; sudo service layer (autocomplete works for any internal user); no HTTP
in `create()`; `get_view` instead of `fields_view_get`; natural-key dedup; no
silent clearing of document addresses.

## Requirements
Odoo 19.0 Community, Python 3.10+, PostgreSQL, Python `requests`.

## Install
```
odoo-bin -d <db> -i dm_geodata_online
# tests:
odoo-bin -d <db> -i dm_test_geodata_connector --test-enable --stop-after-init
```
