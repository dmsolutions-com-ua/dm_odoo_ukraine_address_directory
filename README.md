# Адресний довідник України для Odoo 19

[![Odoo](https://img.shields.io/badge/Odoo-19.0-714B67)](https://www.odoo.com)
[![License: LGPL-3](https://img.shields.io/badge/License-LGPL_v3-blue.svg)](LICENSE)
[![Tests](https://img.shields.io/badge/tests-82%20passing-brightgreen)](dm_test_geodata_connector)

Самодостатня інтеграція з API **[Geodata.online](https://geodata.online)** для
автозаповнення, нормалізації та геокодування українських адрес безпосередньо на
картках Odoo (контакти, компанії, CRM, HR, банки, постачальники обідів).

> Без майстрів (wizard) — лише вбудована автопідказка в полях «Місто» / «Вулиця».
> Двомовність адрес: українська + англійська транслітерація (без російської).

## Можливості
- Вбудована автопідказка міст / вулиць / будинків із джерела Geodata.online.
- Нормалізація адреси, КАТОТТГ/КОАТУУ, поштовий індекс, район, громада, метро.
- Геокодування (широта/довгота) через провайдера `base_geolocalize`.
- Готові адреси для документів і конвертів (UA/EN) + конфігуровані HTML-колонки
  «Деталі адреси» на вкладці картки.
- Мультикомпанійна ізоляція облікових даних і логів через `ir.rule`.
- Проактивний моніторинг стану API (cron + жива нотифікація менеджерам).

## Модулі
| Модуль | Призначення |
|--------|-------------|
| `dm_geodata_connector` | Ядро: модель адреси, власний API-клієнт, OWL-віджет автопідказки, геокодер, безпека, моніторинг |
| `dm_geodata_online` | Парасольковий застосунок: встановлює набір |
| `dm_geodata_contact` | Автопідказка на `res.partner` |
| `dm_geodata_crm` | Автопідказка на `crm.lead` (auto-install bridge) |
| `dm_geodata_company` | Автопідказка на `res.company` (auto-install bridge) |
| `dm_geodata_hr` | Автопідказка на приватну адресу `hr.employee` (auto-install bridge) |
| `dm_geodata_bank` | Автопідказка на `res.bank` (auto-install bridge) |
| `dm_geodata_lunch` | Автопідказка на `lunch.supplier` (потребує `lunch`) |
| `dm_test_geodata_connector` | Mock API + юніт-тести (лише для тестових БД) |

> Усі bridge-модулі тонкі: перевикористовують спільний `dm.geodata.address.mixin`
> (нова модель-власник = мапа `_geodata_fields` + в'юха, ~100–150 рядків).

## Вимоги
Odoo 19.0 Community, Python 3.10+, PostgreSQL, Python-пакет `requests`.

## Встановлення
```bash
# увесь набір (через парасольковий застосунок):
odoo-bin -d <db> -i dm_geodata_online

# тести:
odoo-bin -d <db> -i dm_test_geodata_connector --test-enable --stop-after-init
```
Після встановлення задайте облікові дані API у **Налаштування → Geodata.online**.

## Гілки
- `main` — основна гілка розробки.
- `19.0` — гілка серії Odoo для публікації в [Odoo Apps Store](https://apps.odoo.com)
  (підключення репозиторію через `#19.0`).

## Документація
Технічні матеріали — у теці [`doc/`](doc/): опис API та приклади
запитів/відповідей (токени в прикладах знеособлені — `{{token}}`).

## Ліцензія
[LGPL-3](LICENSE) — безкоштовний модуль із відкритим кодом.

## Автор
**DM Solutions** · [geodata.online](https://geodata.online)
