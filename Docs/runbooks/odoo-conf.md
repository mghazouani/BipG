# Odoo configuration (`odoo.conf`)

## Where it lives

- Repo file: `liv-poc/odoo.conf`
- Container path: `/etc/odoo/odoo.conf` (mounted **read-only** by Docker Compose)

In `docker-compose.yml`:

- `./odoo.conf:/etc/odoo/odoo.conf:ro`

## What it configures (current POC)

`odoo.conf` currently sets:

- **Database connection**
  - `db_host = db`
  - `db_port = 5432`
  - `db_user = odoo`
  - `db_password = odoo`
- **Filestore / data directory**
  - `data_dir = /var/lib/odoo`
- **Addons**
  - `addons_path = /mnt/extra-addons` (mapped to `./odoo-addon/` via Docker volume)

## Why commands don’t need DB flags

When you run Odoo commands inside the container (e.g. module upgrade), **do not pass DB flags** (like `-d`, `--db-filter`, etc.). Odoo reads the DB connection from `/etc/odoo/odoo.conf`.

Example (module upgrade):

```bash
docker compose exec odoo odoo -u liv_delivery --stop-after-init
```

## Common failure mode: Unix socket fallback

If `db_host` is missing, Odoo may fall back to a local **Unix socket** connection, which does not work in this Docker Compose setup (Postgres runs in the `db` service).

Fix: ensure `db_host = db` is present in `odoo.conf`.

## Why `data_dir` matters

Odoo’s filestore is stored under `data_dir`. Setting `data_dir = /var/lib/odoo` keeps the filestore path consistent with what the database expects inside the container (matches the default data volume in this compose setup).

## Changing configuration

- Edit `liv-poc/odoo.conf` on the host.
- Restart the `odoo` container for changes to take effect.

## Module upgrade (reference command)

```bash
docker compose exec odoo odoo -u liv_delivery --stop-after-init
```

- No `-d`, no `--db_host` required — read from `odoo.conf`.
- First install (if module not yet present): replace `-u` with `-i`.
- Verified: `2026-02-20` — upgrade completed without DB flags (proof: `database: odoo@db:5432` in Odoo logs).

## Notes / safety

- The credentials in this file are **POC defaults**. Do not reuse for production.
- Avoid putting production secrets in Git-tracked config files.

