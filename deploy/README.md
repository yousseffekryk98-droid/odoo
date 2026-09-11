# TEQ Trust Egypt ERP Deployment

This folder contains the Docker deployment for the `teq-trust-egypt-erp` branch.

## Requirements

- Docker Engine
- Docker Compose v2
- Git

## First deployment

1. Clone the repository and switch to the TEQ branch:

   ```bash
   git clone -b teq-trust-egypt-erp https://github.com/yousseffekryk98-droid/odoo.git
   cd odoo
   ```

2. Create the private environment file:

   ```bash
   cp deploy/env.example deploy/.env
   ```

3. Edit `deploy/.env` and replace both example passwords with strong unique values.

4. Initialize the database, install `teq_trust_core`, and start the stack:

   ```bash
   bash deploy/scripts/init.sh
   ```

5. Open Odoo at:

   `http://SERVER_IP:8069`

The TEQ installer uses database name `teq_trust` by default and installs the Odoo dependencies declared by `teq_trust_core`.

## Normal operation

Start/restart:

```bash
docker compose --env-file deploy/.env -f docker-compose.teq.yml up -d
```

Status:

```bash
docker compose --env-file deploy/.env -f docker-compose.teq.yml ps
```

Logs:

```bash
docker compose --env-file deploy/.env -f docker-compose.teq.yml logs -f odoo
```

Stop:

```bash
docker compose --env-file deploy/.env -f docker-compose.teq.yml down
```

Do not add `-v` to `down` unless you intentionally want to delete the PostgreSQL and Odoo persistent volumes.

## Backups

Create a PostgreSQL dump and matching Odoo filestore archive:

```bash
bash deploy/scripts/backup.sh
```

Backups are written to `deploy/backups/` and are ignored by Git. The default retention period is 14 days and can be changed in `deploy/.env`.

For production, copy backups to a second machine or object-storage service. A backup that exists only on the ERP server is not sufficient disaster recovery.

## Restore

Restore a matching database dump and filestore archive:

```bash
bash deploy/scripts/restore.sh \
  deploy/backups/teq_trust_YYYYMMDD_HHMMSS.dump \
  deploy/backups/teq_trust_YYYYMMDD_HHMMSS_filestore.tar.gz
```

The restore script replaces the configured TEQ database and filestore. Use it only with verified backup files.

## Production reverse proxy

For a public production server:

- Put Nginx, Caddy, Cloudflare Tunnel, or another trusted reverse proxy in front of Odoo.
- Enable HTTPS.
- Change `ODOO_BIND=127.0.0.1` when the proxy runs on the same host.
- Set `ODOO_PROXY_MODE=True` only when Odoo is actually behind a trusted proxy.
- Keep PostgreSQL unexposed to the public Internet.
- Keep `ODOO_LIST_DB=False`.
- Use a firewall so only required ports are reachable.

## Production sizing

The template starts with `ODOO_WORKERS=0` to simplify first installation and troubleshooting. After the first successful functional test, set the worker count based on the actual CPU/RAM available on the TEQ server and run load tests before production use.

## Updating TEQ code

```bash
git checkout teq-trust-egypt-erp
git pull
docker compose --env-file deploy/.env -f docker-compose.teq.yml run --rm --no-deps odoo \
  -d teq_trust -u teq_trust_core --stop-after-init
docker compose --env-file deploy/.env -f docker-compose.teq.yml up -d
```

If `ODOO_DB_NAME` is changed from `teq_trust`, replace the database name in the update command accordingly.

## Security notes

- `deploy/.env` is ignored by Git and must never be committed.
- Never use the example passwords from `env.example`.
- The Odoo database master password is different from an Odoo user login password.
- Back up both PostgreSQL and the Odoo filestore; one without the other is incomplete.
- Test restore procedures before depending on backups for production.
