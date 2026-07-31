# Міграція неймінгу плейсхолдерів (Підхід A):
#  - address_format_document/_letter/_display: якщо = старий дефолт -> новий
#    чистий дефолт (стандартні поля Odoo = фактична адреса); інакше (кастом) —
#    перейменування CamelCase->gd_ (точна стара поведінка: значення з довідника);
#  - block_format_*/details_format_col1/col2: перейменування CamelCase->gd_
#    (їхній новий дефолт = gd_-версія старого, тож окремого спец-кейсу не треба).
import logging
import re

from odoo import SUPERUSER_ID, api

_logger = logging.getLogger(__name__)

# Старі літерали дефолтів (для точного порівняння з невимірними значеннями).
_OLD_DOC = (
    "{country}, {Index_}, {Region}, {Area}, {Hromada}, "
    "{SettlementType} {City}, {StrType} {Street}, {HouseNum}{HouseNumAdd}, "
    "{ApartmentType} {Apartment}"
)
_OLD_LETTER = (
    "{StrType} {Street}, {HouseNum}{HouseNumAdd}, "
    "{ApartmentType} {Apartment}, {SettlementType} {City}, "
    "{Area}, {Region}, {Index_}"
)
_OLD_DISPLAY = (
    "{country}, {Index_}, {Region} ({RegionOld}), {Area} ({AreaOld}), "
    "{HromadaFull}, {CityFull}, "
    "({CityDistrict} район міста), {StreetFull}, {HouseNum}{HouseNumAdd}, "
    "{ApartmentType}, {Apartment}, {street2}, {AdditionAddress}"
)

_PLACEHOLDER_RE = re.compile(r"\{(\w+)\}")

# Поля з `gd_`-плейсхолдерами (block/details) — просто перейменувати.
_GD_ONLY_FIELDS = (
    "block_format_city", "block_format_street", "block_format_street2",
    "block_format_area", "block_format_hromada",
    "details_format_col1", "details_format_col2",
)


def _rename(text, gd_map):
    if not text:
        return text
    return _PLACEHOLDER_RE.sub(
        lambda m: "{%s}" % gd_map.get(m.group(1), m.group(1)), text)


def migrate(cr, version):
    env = api.Environment(cr, SUPERUSER_ID, {})
    Cred = env["dm.geodata.api.credential"]
    gd_map = env["dm.geodata.address"]._GD_KEYS

    # Нові дефолти беремо прямо з полів моделі (єдине джерело істини).
    defaults = Cred.default_get([
        "address_format_document", "address_format_letter",
        "address_format_display",
    ])
    addr_fields = {
        "address_format_document": (_OLD_DOC, defaults.get("address_format_document")),
        "address_format_letter": (_OLD_LETTER, defaults.get("address_format_letter")),
        "address_format_display": (_OLD_DISPLAY, defaults.get("address_format_display")),
    }

    creds = Cred.with_context(active_test=False).search([])
    for cred in creds:
        vals = {}
        for fname, (old, new) in addr_fields.items():
            cur = cred[fname]
            if cur == old:
                vals[fname] = new                 # старий дефолт -> новий чистий
            elif cur:
                vals[fname] = _rename(cur, gd_map)  # кастом -> CamelCase->gd_
        for fname in _GD_ONLY_FIELDS:
            cur = cred[fname]
            if cur:
                renamed = _rename(cur, gd_map)
                if renamed != cur:
                    vals[fname] = renamed
        if vals:
            cred.write(vals)
    _logger.info("Geodata: мігровано плейсхолдери шаблонів на %d облікових записах",
                 len(creds))
