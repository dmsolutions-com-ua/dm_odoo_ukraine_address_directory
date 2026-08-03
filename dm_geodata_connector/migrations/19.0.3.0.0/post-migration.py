# Перехід англійської транслітерації з API на локальну функцію (КМУ №55):
#  - усі колонки `*_en` на dm.geodata.address стали computed+stored від своїх
#    UA-полів. Odoo перераховує лише НОВІ колонки, а ці вже існували, тож
#    наявні записи треба поставити в чергу перерахунку явно;
#  - налаштування store_english прибрано (транслітерація тепер завжди) —
#    осиротілу колонку прибираємо з таблиці облікових записів.
# Разом із цим — перерахунок шаблонних адрес: `_api_template_values` тепер дає
# й чисті (owner-)імена, тож дефолтні шаблони на цій моделі більше не
# рендеряться майже порожніми (address_display показував саму «УКРАЇНА», а
# address_letter_* — порожній рядок). Залежності полів не змінились, тож без
# явної черги збережені значення лишились би зіпсованими.
import logging

from odoo import SUPERUSER_ID, api

_logger = logging.getLogger(__name__)


def migrate(cr, version):
    env = api.Environment(cr, SUPERUSER_ID, {})
    Address = env["dm.geodata.address"]
    records = Address.search([])
    if records:
        # Джерело істини — та сама мапа, що живить _compute_translit.
        en_fields = [en for _ua, en in Address._TRANSLIT_FIELDS]
        # Усі шаблонні адреси (не лише EN): їх змінили і транслітерація, і чисті
        # імена в _api_template_values.
        template_fields = [
            "address_display",
            "address_full_ua", "address_letter_ua",
            "address_full_en", "address_letter_en",
        ]
        for fname in en_fields + template_fields:
            env.add_to_compute(Address._fields[fname], records)
        records.flush_recordset()

    cr.execute(
        "ALTER TABLE dm_geodata_api_credential DROP COLUMN IF EXISTS store_english")

    _logger.info(
        "Geodata: локальна транслітерація та шаблонні адреси перераховані для "
        "%d адрес; налаштування store_english прибрано", len(records))
