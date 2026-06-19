import logging

from . import models

_logger = logging.getLogger(__name__)


def post_init_hook(env):
    """Sync Ukraine administrative regions (oblasts) from JSON reference
    data into ``res.country.state`` after install/upgrade.

    Idempotent: existing states are matched by code and updated/skipped.
    Failures are logged at WARNING level so they are visible (unlike the
    previous version which silenced them at debug level).
    """
    from .models.res_country_state_sync import UkraineStatesSync

    try:
        stats = UkraineStatesSync.sync_ukraine_states(env)
        _logger.info(
            "Ukraine states sync: created=%s updated=%s skipped=%s",
            stats.get("created"),
            stats.get("updated"),
            stats.get("skipped"),
        )
    except Exception:  # noqa: BLE001 - hook must not block install
        _logger.warning("Ukraine states sync failed during post_init", exc_info=True)

    # Прив'язуємо щоденну перевірку балансу/токену до 01:MM за Києвом (MM = версія
    # Odoo). Робиться тут, бо XML не вміє рахувати часову зону/версію; виконується і
    # на install, і на `-u`, тож кожне оновлення модуля переставляє час і коригує
    # накопичений DST-зсув.
    try:
        cron = env.ref(
            "dm_geodata_connector.cron_geodata_health_check",
            raise_if_not_found=False,
        )
        if cron:
            cron.write({
                "nextcall": env[
                    "dm.geodata.api.credential"
                ]._geodata_health_nextcall(),
                "interval_number": 1,
                "interval_type": "days",
            })
    except Exception:  # noqa: BLE001 - hook must not block install
        _logger.warning(
            "Geodata health cron scheduling failed during post_init", exc_info=True)
