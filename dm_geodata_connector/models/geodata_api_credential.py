import logging
from datetime import timedelta

import pytz
import requests

from odoo import _, api, fields, models, release
from odoo.exceptions import UserError, ValidationError

_logger = logging.getLogger(__name__)

# Відповіді Geodata API, що трактуються як порожні, але валідні.
_EMPTY_RESULT_MESSAGES = frozenset(
    {
        "No cities for this filter.",
        "No streets for this filter or moniker was expired.",
        "No houses for this filter or moniker was expired.",
        "No apartments for this filter or moniker was expired.",
        "Nothing found",
    }
)
_MONIKER_EXPIRED = "Moniker expired"


class GeodataApiCredential(models.Model):
    _name = "dm.geodata.api.credential"
    _description = "Geodata API Credential"
    _order = "id desc"

    # Odoo 19: застарілий список `_sql_constraints` ігнорується -> models.Constraint.
    _name_uniq = models.Constraint(
        "UNIQUE (name)",
        "Credential name must be unique.",
    )

    # Дефолтний шаблон документної адреси: імена плейсхолдерів = імена полів API;
    # значення сирі (без авто-склейок). Порожні поля не лишають «, ,» (рушій
    # стискає роздільники).
    _DEFAULT_ADDRESS_FORMAT = (
        "{country}, {Index_}, {Region}, {Area}, {Hromada}, "
        "{SettlementType} {City}, {StrType} {Street}, {HouseNum}{HouseNumAdd}, "
        "{ApartmentType} {Apartment}"
    )

    name = fields.Char(required=True, default="Geodata.online")
    active = fields.Boolean(default=True)
    company_id = fields.Many2one(
        comodel_name="res.company",
        string="Company",
        help="Leave empty to make this credential available to all companies.",
    )
    api_url = fields.Char(
        string="API URL",
        required=True,
        default="https://api.dmsolutions.com.ua:2661",
    )
    # Секрети платного акаунта Geodata.online: обмежені адмінами Налаштувань на
    # рівні ORM (`groups`), тож їх не можна прочитати через RPC/експорт звичайними
    # користувачами чи не-системними менеджерами. Серверні потоки читають їх через
    # sudo (див. `_refresh_token`), тож автопідказка / Перевірка з'єднання працюють.
    api_username = fields.Char(
        string="Username", required=True, groups="base.group_system")
    api_password = fields.Char(
        string="Password", required=True, groups="base.group_system")
    store_english = fields.Boolean(
        string="Store English Transliteration",
        default=True,
    )
    # Шаблони адрес (документи/конверти): імена плейсхолдерів = імена полів API,
    # значення сирі 1:1 (без авто-склейок). {CityFull}/{StreetFull} — розумне
    # відображення зі старими назвами.
    address_format_document = fields.Char(
        string="Document address template", default=_DEFAULT_ADDRESS_FORMAT)
    address_format_letter = fields.Char(
        string="Envelope address template",
        default=(
            "{StrType} {Street}, {HouseNum}{HouseNumAdd}, "
            "{ApartmentType} {Apartment}, {SettlementType} {City}, "
            "{Area}, {Region}, {Index_}"
        ))
    # Перший рядок (повна адреса) на вкладці «Інформація про адресу» картки контакту.
    address_format_display = fields.Char(
        string="Contact address line template",
        default=(
            "{country}, {Index_}, {Region} ({RegionOld}), {Area} ({AreaOld}), "
            "{HromadaFull}, {CityFull}, "
            "({CityDistrict} район міста), {StreetFull}, {HouseNum}{HouseNumAdd}, "
            "{ApartmentType}, {Apartment}, {street2}, {AdditionAddress}"
        ))
    # Дві колонки «Деталі адреси» на вкладці картки контакту (HTML; порожні рядки
    # ховаються; значення екрануються).
    details_format_col1 = fields.Text(
        string="Address details: column 1",
        default='''<table style="border-collapse:collapse; width:100%;">
<tr><td style="padding:6px 0; border-bottom:1px solid #E6E6E6;"><strong>КАТОТТГ:</strong></td><td style="padding:6px 0; border-bottom:1px solid #E6E6E6;">{KATO}</td></tr>
<tr><td style="padding:6px 0; border-bottom:1px solid #E6E6E6;"><strong>КОАТУУ:</strong></td><td style="padding:6px 0; border-bottom:1px solid #E6E6E6;">{KOATUU}</td></tr>
<tr><td style="padding:6px 0; border-bottom:1px solid #E6E6E6;"><strong>Інформація на дату:</strong></td><td style="padding:6px 0; border-bottom:1px solid #E6E6E6;">{updated}</td></tr>
</table>''')
    details_format_col2 = fields.Text(
        string="Address details: column 2",
        default='''<span style="display:inline-block;background:#009739;color:#fff;font-weight:bold;padding:2px 6px;border-radius:4px;font-size:12px;margin-left:6px;margin-right:4px;">М</span><span style="display:inline-block;background:#009739;color:#fff;padding:2px 6px;border-radius:4px;font-size:12px;margin-right:4px;">{MetroStation}</span>
<span style="display:inline-block;background:#0057B8;color:#fff;padding:2px 6px;border-radius:4px;font-size:12px;margin-right:4px;">{MetroLine}</span>
<span style="display:inline-block;background:#555;color:#fff;padding:2px 6px;border-radius:4px;font-size:12px;">{MetroDistance} м</span>
<table style="border-collapse:collapse; width:100%; font-family:Arial, sans-serif;">
<tr><td style="padding:6px; width:50%;"><a href="https://www.google.com/maps?q={Lat_},{Long_}" target="_blank" style="display:block;text-align:center;background:#1a73e8;color:#fff;font-weight:bold;padding:6px 0;border-radius:4px;font-size:12px;text-decoration:none;">Google Maps</a></td><td style="padding:6px; width:50%;"><a href="https://www.openstreetmap.org/?mlat={Lat_}&mlon={Long_}#map=18/{Lat_}/{Long_}" target="_blank" style="display:block;text-align:center;background:#77B255;color:#fff;font-weight:bold;padding:6px 0;border-radius:4px;font-size:12px;text-decoration:none;">OpenStreetMap</a></td></tr>
<tr><td style="padding:6px;"><span style="display:block;text-align:center;background:#F4B400;color:#000;font-weight:normal;padding:6px 0;border-radius:4px;font-size:12px;">{TerrStatus}</span></td></tr>
</table>''')
    # Шаблони заповнення стандартних полів адресного блоку Odoo з даних API.
    block_format_city = fields.Char(
        string="City field template", default="{CityFull}")
    block_format_street = fields.Char(
        string="Street field template",
        default="{StreetFull}, {HouseNum}{HouseNumAdd}")
    block_format_street2 = fields.Char(
        string="Street 2 field template", default="")
    block_format_area = fields.Char(
        string="District field template", default="{Area} ({AreaOld})")
    block_format_hromada = fields.Char(
        string="Hromada field template", default="{HromadaFull}")

    # Налаштування клієнтського троттлінгу, які споживає OWL-віджет.
    debounce_ms = fields.Integer(string="Autocomplete debounce (ms)", default=250)
    min_chars = fields.Integer(string="Min characters", default=3)
    show_manual_hint = fields.Boolean(
        string="Highlight manual address data",
        default=True,
        help="Mark non-empty address fields that were entered manually (not "
        "chosen from the directory) with a red border and an info icon.",
    )

    is_log_enabled = fields.Boolean(string="Log API requests", default=True)
    log_retention_days = fields.Integer(string="Log retention (days)", default=30)

    payment_notification_interval = fields.Integer(
        string="Alert Interval (minutes)", default=60,
        help="Minimum gap between repeated admin alerts (low balance / payment "
        "required / server unreachable), to avoid spamming.",
    )
    payment_notification_last = fields.Datetime(
        string="Last Payment Alert", readonly=True
    )

    # ------------------------------------------------------------------
    # Проактивний моніторинг стану (для адміна). Креденшал перевіряється щоденним
    # cron (і на вимогу кнопкою у формі); результат відображається як статус у
    # формі, пишеться в серверний лог і надсилається менеджерам Geodata живим
    # попапом (bus-сповіщення). Доповнює реактивний шлях HTTP-402
    # (`_notify_payment_required`).
    # ------------------------------------------------------------------
    health_check_enabled = fields.Boolean(
        string="Enable health monitoring", default=True,
        help="Periodically verify server reachability, authentication and "
        "account balance, and alert managers on problems.",
    )
    balance_alert_threshold = fields.Float(
        string="Low balance threshold", default=0.0,
        help="Raise a warning when the account balance is at or below this value "
        "(0 = alert only once the balance is exhausted).",
    )
    health_status = fields.Selection(
        selection=[
            ("unknown", "Not checked"),
            ("ok", "OK"),
            ("warning", "Warning"),
            ("error", "Error"),
        ],
        string="Health Status", default="unknown", readonly=True, copy=False,
    )
    health_message = fields.Char(string="Health Detail", readonly=True, copy=False)
    health_last_check = fields.Datetime(string="Last Health Check", readonly=True, copy=False)
    last_balance = fields.Float(string="Last Known Balance", readonly=True, copy=False)
    health_alert_last = fields.Datetime(
        string="Last Health Alert", readonly=True, copy=False
    )

    # ------------------------------------------------------------------
    # Зберігання токена (поза таблицею; AUDIT #11)
    # ------------------------------------------------------------------
    def _token_param_key(self):
        self.ensure_one()
        return "dm_geodata_connector.access_token.%s" % self.id

    def _get_token(self):
        self.ensure_one()
        return self.env["ir.config_parameter"].sudo().get_param(
            self._token_param_key()
        )

    def _set_token(self, token):
        self.ensure_one()
        self.env["ir.config_parameter"].sudo().set_param(
            self._token_param_key(), token or ""
        )

    # ------------------------------------------------------------------
    # Життєвий цикл
    # ------------------------------------------------------------------
    def write(self, vals):
        # Скидаємо кешований токен при зміні облікових даних. Ніколи не запускаємо
        # тут повний перерахунок усіх адрес (AUDIT #6).
        res = super().write(vals)
        if "api_username" in vals or "api_password" in vals:
            for rec in self:
                rec._set_token(False)
        return res

    @api.constrains("min_chars")
    def _check_min_chars(self):
        for rec in self:
            if rec.min_chars < 3:
                raise ValidationError(_("Min characters cannot be less than 3."))

    # Валідації шаблонів немає навмисно: імена плейсхолдерів = імена полів API,
    # перелік гнучкий; невідомий плейсхолдер рендериться як порожнє значення.

    # ------------------------------------------------------------------
    # Пошук облікових даних
    # ------------------------------------------------------------------
    @api.model
    def get_credential(self, company=None):
        """Return the active credential for ``company`` (or current),
        falling back to a company-less (global) credential.
        """
        company = company or self.env.company
        return self.sudo().search(
            [
                ("active", "=", True),
                ("company_id", "in", [company.id, False]),
            ],
            limit=1,
            order="company_id desc, id desc",
        )

    # ------------------------------------------------------------------
    # HTTP-клієнт (самодостатній; AUDIT замінює kw_api_connector)
    # ------------------------------------------------------------------
    def _build_url(self, endpoint):
        self.ensure_one()
        return "%s/%s" % (
            (self.api_url or "").rstrip("/"),
            (endpoint or "").lstrip("/"),
        )

    def _auth_headers(self):
        self.ensure_one()
        token = self._get_token()
        if not token:
            self._refresh_token()
            token = self._get_token()
        return {
            "Content-Type": "application/json",
            "Accept": "application/json",
            "Authorization": "Bearer %s" % (token or ""),
        }

    def _refresh_token(self):
        self.ensure_one()
        # Читаємо системно-обмежені секрети через sudo, щоб токен можна було
        # оновити незалежно від групи викликача (менеджерська Перевірка з'єднання,
        # автопідказка внутрішнього користувача). Секрети ніколи не повертаються
        # клієнту — використовуються лише для отримання токена тут.
        cred = self.sudo()
        if not cred.api_username or not cred.api_password:
            return False
        try:
            response = requests.post(
                self._build_url("Token"),
                data={
                    "username": cred.api_username,
                    "password": cred.api_password,
                    "grant_type": "password",
                },
                headers={"Content-Type": "application/x-www-form-urlencoded"},
                timeout=60,
            )
        except requests.RequestException as err:
            _logger.warning("Geodata token refresh failed: %s", err)
            return False
        if response.status_code != 200:
            _logger.warning("Geodata token refresh HTTP %s", response.status_code)
            return False
        token = (response.json() or {}).get("access_token")
        if not token:
            return False
        self._set_token(token)
        return True

    def _api_request(self, endpoint, params=None, method="GET", _retried=False, silent=True):
        """Perform a single API request with masked logging, a 60s timeout
        and a single token-refresh retry on HTTP 401. No retry storms.
        """
        self.ensure_one()
        headers = self._auth_headers()
        url = self._build_url(endpoint)
        started = fields.Datetime.now()
        log_vals = {"name": url, "method": method, "headers": headers,
                    "params": str(params or {})}
        try:
            response = requests.request(
                method, url, params=params, headers=headers, timeout=60
            )
        except requests.RequestException as err:
            self.env["dm.geodata.request.log"].log_request(
                self, dict(log_vals, error=str(err))
            )
            if silent:
                return []
            raise UserError(_("Geodata API connection error: %s") % err) from err

        duration = int((fields.Datetime.now() - started).total_seconds() * 1000)
        self.env["dm.geodata.request.log"].log_request(
            self,
            dict(log_vals, code=response.status_code, duration_ms=duration),
        )

        if response.status_code == 401 and not _retried:
            if self._refresh_token():
                return self._api_request(
                    endpoint, params=params, method=method,
                    _retried=True, silent=silent,
                )
        if response.status_code == 402:
            self._notify_payment_required()
            if silent:
                return []
            raise UserError(self._payment_message())

        if response.status_code != 200:
            try:
                data = response.json()
            except ValueError:
                data = {}
            message = (data.get("Message") or data.get("message") or "").strip()
            if message in _EMPTY_RESULT_MESSAGES:
                return []
            if message == _MONIKER_EXPIRED:
                return {"_moniker_expired": True}
            if silent:
                return []
            raise UserError(
                _("Geodata API error [%(code)s]: %(msg)s",
                  code=response.status_code, msg=message or response.text)
            )
        try:
            return response.json()
        except ValueError:
            return []

    # ------------------------------------------------------------------
    # Сповіщення про оплату (402)
    # ------------------------------------------------------------------
    def _payment_message(self):
        return _(
            "Insufficient funds on your Geodata.online account. "
            "Please top up your balance at https://geodata.online/"
        )

    def _notify_payment_required(self):
        self.ensure_one()
        interval = self.payment_notification_interval or 0
        last = self.payment_notification_last
        if interval > 0 and last:
            elapsed = (fields.Datetime.now() - last).total_seconds() / 60.0
            if elapsed < interval:
                return
        try:
            self.env["bus.bus"]._sendone(
                self.env.user.partner_id,
                "simple_notification",
                {
                    "type": "danger",
                    "title": _("Geodata.online"),
                    "message": self._payment_message(),
                    "sticky": True,
                },
            )
            self.sudo().write({"payment_notification_last": fields.Datetime.now()})
        except Exception:  # noqa: BLE001
            _logger.debug("Failed to send payment bus notification", exc_info=True)

    # ------------------------------------------------------------------
    # Проактивний моніторинг стану (cron + кнопка вручну)
    # ------------------------------------------------------------------
    def _probe_health(self):
        """Probe the API once (silent) and classify the result.

        Returns a dict ``{status, message, balance}`` where status is one of
        ``ok`` / ``warning`` / ``error``. Never raises - safe to call from a
        cron. The request is logged like any other (`dm.geodata.request.log`)."""
        self.ensure_one()
        info = self.api_user_info(silent=True)
        if not info or not info.get("Email"):
            return {
                "status": "error",
                "message": _(
                    "Geodata.online server unreachable or invalid credentials "
                    "(no account info returned)."
                ),
                "balance": 0.0,
            }
        balance = float(info.get("Balans") or 0.0)
        if balance <= (self.balance_alert_threshold or 0.0):
            return {
                "status": "warning",
                "message": _(
                    "Low Geodata.online balance: %(balance).2f (threshold "
                    "%(threshold).2f). Top up at https://geodata.online/",
                    balance=balance, threshold=self.balance_alert_threshold or 0.0,
                ),
                "balance": balance,
            }
        return {
            "status": "ok",
            "message": _("OK. Balance: %.2f", balance),
            "balance": balance,
        }

    def _run_health_check(self):
        """Probe each record, store the outcome and alert managers on problems."""
        for rec in self:
            result = rec._probe_health()
            rec.sudo().write({
                "health_status": result["status"],
                "health_message": result["message"],
                "last_balance": result["balance"],
                "health_last_check": fields.Datetime.now(),
            })
            if result["status"] == "error":
                _logger.error("Geodata health [%s]: %s", rec.name, result["message"])
                rec._alert_managers(result["message"], "danger")
            elif result["status"] == "warning":
                _logger.warning("Geodata health [%s]: %s", rec.name, result["message"])
                rec._alert_managers(result["message"], "warning")
            else:
                _logger.info("Geodata health [%s]: %s", rec.name, result["message"])
        return True

    def _alert_managers(self, message, level="warning"):
        """Push a throttled live popup to every Geodata manager.

        Uses the same `bus.bus` notification as the reactive payment alert, but
        targets the managers group (the people who can act) instead of the
        current user, and is durably backed by the server log."""
        self.ensure_one()
        interval = self.payment_notification_interval or 0
        last = self.health_alert_last
        if interval > 0 and last:
            elapsed = (fields.Datetime.now() - last).total_seconds() / 60.0
            if elapsed < interval:
                return
        # Креденшал конкретної компанії стосується лише менеджерів тієї компанії;
        # глобальний креденшал (без компанії) стосується всіх.
        partners = self._geodata_manager_partners(self.company_id)
        try:
            self._geodata_push(partners, message, level)
            self.sudo().write({"health_alert_last": fields.Datetime.now()})
        except Exception:  # noqa: BLE001
            _logger.debug("Failed to send Geodata health bus notification", exc_info=True)

    @api.model
    def _geodata_manager_partners(self, company=None):
        """Partners of Geodata managers, optionally restricted to a company
        (only managers who have that company in their allowed companies)."""
        managers = self.env.ref(
            "dm_geodata_connector.group_geodata_manager", raise_if_not_found=False
        )
        users = managers.user_ids if managers else self.env["res.users"]
        if company:
            users = users.filtered(lambda u: company.id in u.company_ids.ids)
        return users.partner_id

    @api.model
    def _geodata_push(self, partners, message, level):
        for partner in partners:
            self.env["bus.bus"]._sendone(
                partner,
                "simple_notification",
                {
                    "type": level,
                    "title": _("Geodata.online"),
                    "message": message,
                    "sticky": True,
                },
            )

    def action_health_check(self):
        """Form button: run the health check now and report the outcome."""
        self.ensure_one()
        self._run_health_check()
        type_map = {"ok": "success", "warning": "warning", "error": "danger"}
        return {
            "type": "ir.actions.client",
            "tag": "display_notification",
            "params": {
                "title": _("Geodata.online health check"),
                "message": self.health_message or "",
                "type": type_map.get(self.health_status, "info"),
                "sticky": self.health_status == "error",
            },
        }

    @api.model
    def _geodata_health_nextcall(self):
        """Наступний момент 01:MM за Києвом у вигляді naive-UTC для ir.cron.nextcall.

        Хвилина MM = мажорна версія Odoo (18/19/20) — той самий код коректний на всіх
        гілках. Базова година 01:00 (а не 00:00) обрана навмисно: ir.cron.nextcall
        зберігається в UTC і при переході на літній/зимовий час може зсунутись на
        ±1 год; старт о 01:MM тримає фактичний запуск у діапазоні 00:MM…02:MM, тож він
        ніколи не «втікає» в попередній день."""
        try:
            tz = pytz.timezone("Europe/Kyiv")
        except pytz.UnknownTimeZoneError:
            tz = pytz.timezone("Europe/Kiev")  # старіші tzdata
        minute = release.version_info[0] % 60
        local = pytz.utc.localize(fields.Datetime.now()).astimezone(tz)
        target = local.replace(hour=1, minute=minute, second=0, microsecond=0)
        if target <= local:
            target += timedelta(days=1)
        return target.astimezone(pytz.utc).replace(tzinfo=None)

    @api.model
    def _cron_health_check(self):
        """Daily scheduled health check, multi-company aware.

        (a) Probes every active credential (its alerts are company-scoped).
        (b) Per-company gap detection: a company for which no active credential
        resolves has silent autocomplete, so it is logged and pushed to that
        company's managers."""
        creds = self.sudo().search([("active", "=", True)])
        creds.filtered("health_check_enabled")._run_health_check()
        for company in self.env["res.company"].sudo().search([]):
            if self.get_credential(company):
                continue
            message = _(
                "Geodata.online: no active API credential is configured for "
                "company '%(company)s' - address autocomplete will not work there. "
                "Configure one under Settings -> Geodata.online -> API Credentials.",
                company=company.display_name,
            )
            _logger.warning(message)
            self._alert_managers_no_credential(message, company)
        return True

    @api.model
    def _alert_managers_no_credential(self, message, company=None):
        """Push the 'no credential configured' popup to managers (no record to
        attach to, so this is a standalone, un-throttled daily alert), scoped to
        the given company's managers when provided."""
        try:
            self._geodata_push(
                self._geodata_manager_partners(company), message, "warning")
        except Exception:  # noqa: BLE001
            _logger.debug("Failed to send Geodata no-credential notification", exc_info=True)

    # ------------------------------------------------------------------
    # Нормалізація запиту (AUDIT #17) та обгортки API
    # ------------------------------------------------------------------
    @staticmethod
    def _normalize_query(query):
        if not query:
            return ""
        return " ".join(str(query).split())

    def api_full_address(self, query, lang="uk_UA"):
        query = self._normalize_query(query)
        if not query:
            return []
        result = self._api_request("api/FullAddress", {"sRequest": query, "sLang": lang})
        if isinstance(result, dict) and not result.get("_moniker_expired"):
            return [result]
        return result if isinstance(result, list) else []

    def api_address(self, query, lang="uk_UA"):
        query = self._normalize_query(query.replace(",", " ") if query else query)
        if not query:
            return []
        result = self._api_request("api/Address", {"sRequest": query, "sLang": lang})
        if isinstance(result, dict) and not result.get("_moniker_expired"):
            return [result]
        return result if isinstance(result, list) else []

    def api_cities(self, query="", lang="uk_UA", region="", post_code=""):
        query = self._normalize_query(query)
        if not query and not post_code:
            return []
        params = {"sLang": lang}
        if post_code:
            params["sPostCode"] = post_code
        else:
            params["sRequest"] = query
        if region:
            params["sRegion"] = region
        result = self._api_request("api/Cities", params)
        return result if isinstance(result, list) else []

    def api_streets(self, query, moniker, lang="uk_UA"):
        query = self._normalize_query(query)
        if not query or not moniker:
            return []
        return self._api_request(
            "api/Streets", {"sRequest": query, "stMoniker": moniker, "sLang": lang}
        )

    def api_houses(self, query, moniker, lang="uk_UA"):
        query = self._normalize_query(query)
        if not query or not moniker:
            return []
        return self._api_request(
            "api/Houses", {"sRequest": query, "houseMoniker": moniker, "sLang": lang}
        )

    # ------------------------------------------------------------------
    # Переотримання monikers (живуть ~15 хв; прозоро оновлюються зі збережених
    # КАТОТТГ/посилань — без кнопок).
    # ------------------------------------------------------------------
    def _resolve_city_moniker(self, geo_addr, lang="uk_UA"):
        self.ensure_one()
        results = []
        post = geo_addr.kato or geo_addr.koatuu
        if post:
            results = self.api_cities(post_code=post, lang=lang)
        if not results and geo_addr.city:
            results = self.api_cities(
                geo_addr.city, lang=lang, region=geo_addr.region or "")
        for r in results:
            if not isinstance(r, dict):
                continue
            rid = r.get("SettlementId") or r.get("Id")
            if geo_addr.settlement_ref and rid and int(rid) == geo_addr.settlement_ref:
                return r.get("st_moniker") or r.get("Moniker") or ""
        if results and isinstance(results[0], dict):
            return results[0].get("st_moniker") or results[0].get("Moniker") or ""
        return ""

    def _resolve_street_moniker(self, geo_addr, city_moniker, lang="uk_UA"):
        self.ensure_one()
        if not city_moniker or not geo_addr.street:
            return ""
        results = self.api_streets(geo_addr.street, city_moniker, lang=lang)
        if isinstance(results, dict) or not isinstance(results, list):
            return ""
        for r in results:
            if not isinstance(r, dict):
                continue
            if geo_addr.street_ref and str(r.get("StreetId")) == str(geo_addr.street_ref):
                return r.get("house_moniker") or ""
        if results and isinstance(results[0], dict):
            return results[0].get("house_moniker") or ""
        return ""

    def api_user_info(self, silent=False):
        result = self._api_request("api/Account/UserInfo", silent=silent)
        return result if isinstance(result, dict) else {}

    # ------------------------------------------------------------------
    # Дії інтерфейсу
    # ------------------------------------------------------------------
    def action_test_connection(self):
        self.ensure_one()
        if not self._get_token() and not self._refresh_token():
            raise UserError(_("Failed to obtain access token. Check username/password."))
        info = self.api_user_info()
        if not info or not info.get("Email"):
            raise UserError(_("API returned empty user info. Check credentials."))
        self.action_sync_ukraine_states()
        balance = info.get("Balans")
        balance_str = "" if balance is None else "%.2f" % float(balance)
        return {
            "type": "ir.actions.client",
            "tag": "display_notification",
            "params": {
                "title": _("Success"),
                "message": _(
                    "Connection successful. Email: %(email)s, Balance: %(balance)s",
                    email=info.get("Email") or "",
                    balance=balance_str,
                ),
                "type": "success",
                "sticky": False,
            },
        }

    def action_sync_ukraine_states(self):
        self.ensure_one()
        from .res_country_state_sync import UkraineStatesSync

        stats = UkraineStatesSync.sync_ukraine_states(self.env)
        return {
            "type": "ir.actions.client",
            "tag": "display_notification",
            "params": {
                "title": _("Success"),
                "message": _(
                    "Ukraine states synced: created=%(c)s updated=%(u)s skipped=%(s)s",
                    c=stats.get("created"), u=stats.get("updated"), s=stats.get("skipped"),
                ),
                "type": "success",
                "sticky": False,
            },
        }
