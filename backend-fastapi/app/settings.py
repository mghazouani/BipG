import os
import sys

REDIS_URL = os.getenv("REDIS_URL", "redis://localhost:6379/0")

ODOO_URL = os.getenv("ODOO_URL", "http://localhost:8069")
ODOO_DB = os.getenv("ODOO_DB", "odoo")
ODOO_USERNAME = os.getenv("ODOO_USERNAME", "admin")
ODOO_PASSWORD = os.getenv("ODOO_PASSWORD", "admin")

# POC only: enable POST /poc/seed/delivery (default false -> endpoint returns 404)
POC_SEED_ENABLED = os.getenv("POC_SEED_ENABLED", "false").lower() in ("true", "1", "yes")

# Hardening A.1: WS rate limit (min seconds between messages per (delivery_id, driver_id))
TRACK_RATE_LIMIT_SECONDS = int(os.getenv("TRACK_RATE_LIMIT_SECONDS", "10"))
# Max pending Odoo writes per delivery before dropping oldest
ODOO_QUEUE_MAX = int(os.getenv("ODOO_QUEUE_MAX", "50"))
# Exponential backoff for Odoo retries (seconds): initial, max cap
ODOO_BACKOFF_INITIAL = float(os.getenv("ODOO_BACKOFF_INITIAL", "1"))
ODOO_BACKOFF_MAX = float(os.getenv("ODOO_BACKOFF_MAX", "30"))

# Hardening A.2: WS token auth
WS_SECRET = os.getenv("WS_SECRET", "").encode("utf-8") if os.getenv("WS_SECRET") else b""
if not WS_SECRET:
    print("FATAL: WS_SECRET env var is required. Set it and restart.", file=sys.stderr)
    sys.exit(1)
WS_SECRET_PREV = os.getenv("WS_SECRET_PREV", "").encode("utf-8") if os.getenv("WS_SECRET_PREV") else b""
WS_TOKEN_MAX_AGE_SECONDS = int(os.getenv("WS_TOKEN_MAX_AGE_SECONDS", "300"))
WS_TOKEN_MAX_FUTURE_SKEW_SECONDS = int(os.getenv("WS_TOKEN_MAX_FUTURE_SKEW_SECONDS", "30"))
DELIVERY_DRIVER_CACHE_TTL = int(os.getenv("DELIVERY_DRIVER_CACHE_TTL", "600"))

# Hardening A.3: CORS / allowed origins (REST + WS)
_allowed_origins_raw = os.getenv("ALLOWED_ORIGINS", "http://localhost:3000,http://localhost:5173")
ALLOWED_ORIGINS = [o.strip() for o in _allowed_origins_raw.split(",") if o.strip()]

# Secured health status endpoint: Bearer or X-Health-Token must match
HEALTH_SECRET = os.getenv("HEALTH_SECRET", "")
