import json
import logging
from os.path import dirname, join

_logger = logging.getLogger(__name__)


class UkraineStatesSync:
    """Sync Ukraine oblasts from the bundled JSON into res.country.state.

    Idempotent: states are matched by ISO code and updated/skipped. This is
    the ONLY place that creates res.country.state (AUDIT #10).
    """

    @staticmethod
    def _load_data():
        path = join(dirname(dirname(__file__)), "data", "res_country_state_ukraine.json")
        with open(path, encoding="utf-8") as fh:
            return json.load(fh)

    @staticmethod
    def sync_ukraine_states(env):
        stats = {"created": 0, "updated": 0, "skipped": 0}
        try:
            data = UkraineStatesSync._load_data()
        except Exception:  # noqa: BLE001
            _logger.warning("Cannot load Ukraine states JSON", exc_info=True)
            return dict(stats, error=True)

        country = env.ref("base.ua", raise_if_not_found=False)
        if not country:
            _logger.warning("Country Ukraine (base.ua) not found")
            return dict(stats, error=True)

        State = env["res.country.state"].sudo()
        for state_data in data.get("states", []):
            code, name = state_data["code"], state_data["name"]
            existing = State.search(
                [("code", "=", code), ("country_id", "=", country.id)], limit=1
            )
            if existing:
                if existing.name != name:
                    existing.write({"name": name})
                    stats["updated"] += 1
                else:
                    stats["skipped"] += 1
                continue
            State.create({"code": code, "name": name, "country_id": country.id})
            stats["created"] += 1
        return stats
