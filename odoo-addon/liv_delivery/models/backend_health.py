# -*- coding: utf-8 -*-
# NOTE: liv.fastapi_base_url is admin-controlled. In production, restrict it
# to trusted internal URLs to limit SSRF exposure.
import json
import logging
from urllib.request import Request, urlopen
from urllib.error import HTTPError

from odoo import api, fields, models

_logger = logging.getLogger(__name__)

PARAM_BASE_URL = "liv.fastapi_base_url"
PARAM_SECRET = "liv.health_secret"
PARAM_STATUS = "liv.backend_health_status"
PARAM_UPDATED = "liv.backend_health_updated"
PARAM_MESSAGE = "liv.backend_health_message"


class LivBackendHealth(models.AbstractModel):
    _name = "liv.backend.health"
    # The cron is registered on ir.config_parameter as carrier model but
    # executes env['liv.backend.health'].liv_check_backend_health().
    _description = "LIV Backend Health (FastAPI) - no DB model; config-based"

    def _get_param(self, key, default=""):
        return self.env["ir.config_parameter"].sudo().get_param(key, default)

    def _set_param(self, key, value):
        self.env["ir.config_parameter"].sudo().set_param(key, str(value))

    def liv_check_backend_health(self):
        base_url = (self._get_param(PARAM_BASE_URL) or "").strip().rstrip("/")
        secret = (self._get_param(PARAM_SECRET) or "").strip()

        if not base_url:
            self._set_param(PARAM_STATUS, "down")
            self._set_param(PARAM_MESSAGE, "Missing liv.fastapi_base_url")
            self._set_param(PARAM_UPDATED, "")
            _logger.info("liv_backend_health status=down message=Missing liv.fastapi_base_url")
            return

        url = "%s/health/status" % base_url
        headers = {}
        if secret:
            headers["Authorization"] = "Bearer %s" % secret

        try:
            req = Request(url, headers=headers)
            with urlopen(req, timeout=5) as resp:
                status_code = resp.getcode()
                body = resp.read().decode("utf-8", errors="replace")
        except HTTPError as e:
            try:
                status_code = e.code
                body = (e.fp.read().decode("utf-8", errors="replace") if e.fp else "")
            finally:
                if getattr(e, "fp", None) is not None:
                    try:
                        e.fp.close()
                    except Exception:
                        pass
        except Exception as e:
            self._set_param(PARAM_STATUS, "down")
            self._set_param(PARAM_MESSAGE, "Connection error: %s" % type(e).__name__)
            self._set_param(PARAM_UPDATED, "")
            _logger.info(
                "liv_backend_health status=down message=Connection error: %s",
                type(e).__name__,
            )
            return

        if status_code == 401:
            self._set_param(PARAM_STATUS, "auth_error")
            self._set_param(PARAM_MESSAGE, "Unauthorized (check liv.health_secret)")
            self._set_param(PARAM_UPDATED, "")
            _logger.info("liv_backend_health status=auth_error http=401")
            return

        try:
            data = json.loads(body) if body else {}
        except (ValueError, TypeError):
            self._set_param(PARAM_STATUS, "down")
            self._set_param(PARAM_MESSAGE, "Invalid JSON response (HTTP %s)" % status_code)
            self._set_param(PARAM_UPDATED, "")
            _logger.info("liv_backend_health status=down message=Invalid JSON response http=%s", status_code)
            return

        ok = data.get("ok", False)
        redis_ok = data.get("redis", False)
        odoo_ok = data.get("odoo", False)
        ts = data.get("ts", "")
        message = data.get("message", "")

        if status_code == 200 and ok and redis_ok and odoo_ok:
            status = "ok"
        elif redis_ok or odoo_ok:
            status = "degraded"
        else:
            status = "down"

        self._set_param(PARAM_STATUS, status)
        self._set_param(PARAM_UPDATED, ts)
        self._set_param(PARAM_MESSAGE, message or "")
        _logger.info(
            "liv_backend_health status=%s redis=%s odoo=%s http=%s",
            status, redis_ok, odoo_ok, status_code,
        )


class LivBackendHealthDisplay(models.TransientModel):
    _name = "liv.backend.health.display"
    _description = "LIV Backend Health status (read-only)"

    status = fields.Char(readonly=True)
    updated = fields.Char(readonly=True)
    message = fields.Text(readonly=True)
    base_url = fields.Char(readonly=True)

    def _get_display_values(self):
        """Read health params from ir.config_parameter. Never reads PARAM_SECRET."""
        cfg = self.env["ir.config_parameter"].sudo()
        return {
            "status": cfg.get_param(PARAM_STATUS, ""),
            "updated": cfg.get_param(PARAM_UPDATED, ""),
            "message": cfg.get_param(PARAM_MESSAGE, ""),
            "base_url": cfg.get_param(PARAM_BASE_URL, ""),
        }

    @api.model
    def get_display_record(self):
        """Create a transient record with current health values and return it."""
        vals = self._get_display_values()
        return self.create(vals)
