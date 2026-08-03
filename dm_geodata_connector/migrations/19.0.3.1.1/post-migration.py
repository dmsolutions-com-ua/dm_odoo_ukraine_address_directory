# Суфікс громади в EN вирівняно з таблицею КМУ №55: «gr.» -> «hr.» (г -> h,
# громада -> hromada). На боці власника документні адреси — non-stored compute,
# тож вони свіжі самі; а `address_full_en` / `address_letter_en` на
# dm.geodata.address збережені, і дефолтний шаблон містить {hromada}, тож у
# наявних рядках лишився б старий «gr.». Залежності полів не змінились, тож
# Odoo сам їх не перерахує — ставимо в чергу явно.
import logging

from odoo import SUPERUSER_ID, api

_logger = logging.getLogger(__name__)

_TEMPLATE_FIELDS = (
    "address_display",
    "address_full_ua", "address_letter_ua",
    "address_full_en", "address_letter_en",
)


def migrate(cr, version):
    env = api.Environment(cr, SUPERUSER_ID, {})
    Address = env["dm.geodata.address"]
    records = Address.search([])
    if not records:
        return
    for fname in _TEMPLATE_FIELDS:
        env.add_to_compute(Address._fields[fname], records)
    records.flush_recordset()
    _logger.info(
        "Geodata: шаблонні адреси перераховані для %d записів (суфікс громади EN)",
        len(records))
