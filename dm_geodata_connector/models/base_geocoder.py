import logging

from odoo import _, api, models
from odoo.exceptions import UserError

_logger = logging.getLogger(__name__)


class GeoCoder(models.AbstractModel):
    _inherit = "base.geocoder"

    @staticmethod
    def _validate_coordinates(lat, lon, strict_ukraine=False):
        try:
            lat, lon = float(lat), float(lon)
        except (TypeError, ValueError):
            return False
        if strict_ukraine and not (44.0 <= lat <= 52.5 and 22.0 <= lon <= 40.5):
            return False
        return -90 <= lat <= 90 and -180 <= lon <= 180 and (lat != 0 or lon != 0)

    def _call_geodata(self, addr, **kw):
        """Return (lat, lon) for an address string via Geodata.online.

        Pure lookup: does NOT create dm.geodata.address / res.country.state
        as a side effect (AUDIT #10).
        """
        if not addr:
            return None
        credential = self.env["dm.geodata.api.credential"].sudo().get_credential()
        if not credential:
            raise UserError(_("No active Geodata API credential configured."))
        results = credential.api_full_address(addr, lang="uk_UA")
        if not results:
            return None
        data = results[0]
        lat, lon = data.get("Lat_") or data.get("Lat"), data.get("Long_") or data.get("Long")
        if not self._validate_coordinates(lat, lon):
            return None
        return (float(lat), float(lon))

    @api.model
    def _geo_query_address_geodata(self, street=None, zip_code=None, city=None,
                                   state=None, country=None):
        parts = []
        if state:
            parts.append(state if isinstance(state, str) else state.name)
        if city:
            parts.append(city)
        if street:
            parts.append(street)
        if zip_code:
            parts.append(zip_code)
        return ", ".join(p for p in parts if p)
