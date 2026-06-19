import json
import logging

from odoo import api, fields, models

_logger = logging.getLogger(__name__)

# Ключі заголовків, значення яких ніколи не можна зберігати у відкритому вигляді.
_SENSITIVE_HEADERS = ("authorization", "cookie", "set-cookie", "x-api-key")
_MASK = "***"


class GeodataRequestLog(models.Model):
    _name = "dm.geodata.request.log"
    _description = "Geodata API Request Log"
    _order = "create_date desc"

    name = fields.Char(string="URL", required=True)
    company_id = fields.Many2one(
        comodel_name="res.company", index=True,
        default=lambda self: self.env.company,
    )
    method = fields.Char(string="Method")
    headers = fields.Text(string="Headers", help="Request headers (sensitive values masked)")
    params = fields.Text(string="Parameters")
    code = fields.Integer(string="HTTP Status")
    error = fields.Text(string="Error")
    duration_ms = fields.Integer(string="Duration (ms)")
    delete_by_date = fields.Date(string="Delete After", index=True)

    @api.model
    def _mask_headers(self, headers):
        """Return a JSON string of headers with sensitive values masked.

        Prevents leaking the Bearer access token / credentials into logs
        (AUDIT #15).
        """
        if not headers:
            return False
        try:
            masked = {
                key: (_MASK if key.lower() in _SENSITIVE_HEADERS else value)
                for key, value in dict(headers).items()
            }
            return json.dumps(masked, ensure_ascii=False)
        except Exception:  # noqa: BLE001
            return _MASK

    @api.model
    def log_request(self, source, vals):
        """Create a log entry if logging is enabled on the source.

        ``source`` is the credential record; ``vals`` may contain raw
        ``headers`` which are masked here before storage.
        """
        if not source or not source.is_log_enabled:
            return self.browse()
        retention = source.log_retention_days or 0
        delete_by = (
            fields.Date.add(fields.Date.today(), days=retention)
            if retention > 0
            else False
        )
        if "headers" in vals:
            vals = dict(vals, headers=self._mask_headers(vals.get("headers")))
        vals["delete_by_date"] = delete_by
        # Прив'язуємо запис журналу до компанії: власна компанія креденшала, якщо
        # задана, інакше компанія викликача (глобальний креденшал обслуговує будь-кого).
        vals.setdefault("company_id", source.company_id.id or self.env.company.id)
        return self.sudo().create(vals)

    @api.model
    def cron_delete_outdated_logs(self):
        """Remove logs past their retention date (called by ir.cron)."""
        outdated = self.sudo().search(
            [("delete_by_date", "!=", False), ("delete_by_date", "<", fields.Date.today())]
        )
        count = len(outdated)
        outdated.unlink()
        _logger.info("Geodata request log cleanup: removed %s entries", count)
        return count
