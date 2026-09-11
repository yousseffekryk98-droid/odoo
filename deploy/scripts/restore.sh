#!/usr/bin/env bash
set -euo pipefail

if [[ $# -ne 2 ]]; then
  echo "Usage: $0 <database.dump> <filestore.tar.gz>" >&2
  exit 1
fi

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
ENV_FILE="${ROOT_DIR}/deploy/.env"
COMPOSE_FILE="${ROOT_DIR}/docker-compose.teq.yml"
DB_DUMP="$(cd "$(dirname "$1")" && pwd)/$(basename "$1")"
FILESTORE_ARCHIVE="$(cd "$(dirname "$2")" && pwd)/$(basename "$2")"

if [[ ! -f "${ENV_FILE}" ]]; then
  echo "Missing ${ENV_FILE}." >&2
  exit 1
fi
if [[ ! -f "${DB_DUMP}" || ! -f "${FILESTORE_ARCHIVE}" ]]; then
  echo "Backup file not found." >&2
  exit 1
fi

set -a
# shellcheck disable=SC1090
source "${ENV_FILE}"
set +a

DB_NAME="${ODOO_DB_NAME:-teq_trust}"
DB_USER="${POSTGRES_USER:-odoo}"

cd "${ROOT_DIR}"

echo "Stopping Odoo..."
docker compose --env-file "${ENV_FILE}" -f "${COMPOSE_FILE}" stop odoo || true

echo "Recreating database ${DB_NAME}..."
docker compose --env-file "${ENV_FILE}" -f "${COMPOSE_FILE}" up -d db
docker compose --env-file "${ENV_FILE}" -f "${COMPOSE_FILE}" exec -T db \
  psql -U "${DB_USER}" -d postgres -c "SELECT pg_terminate_backend(pid) FROM pg_stat_activity WHERE datname='${DB_NAME}' AND pid <> pg_backend_pid();" >/dev/null
docker compose --env-file "${ENV_FILE}" -f "${COMPOSE_FILE}" exec -T db dropdb -U "${DB_USER}" --if-exists "${DB_NAME}"
docker compose --env-file "${ENV_FILE}" -f "${COMPOSE_FILE}" exec -T db createdb -U "${DB_USER}" "${DB_NAME}"
cat "${DB_DUMP}" | docker compose --env-file "${ENV_FILE}" -f "${COMPOSE_FILE}" exec -T db \
  pg_restore -U "${DB_USER}" -d "${DB_NAME}" --clean --if-exists --no-owner --no-privileges

echo "Restoring filestore..."
cat "${FILESTORE_ARCHIVE}" | docker compose --env-file "${ENV_FILE}" -f "${COMPOSE_FILE}" run -T --rm --no-deps \
  --entrypoint /bin/bash odoo -c "rm -rf /var/lib/odoo/filestore && mkdir -p /var/lib/odoo && tar -C /var/lib/odoo -xzf -"

echo "Starting TEQ ERP..."
docker compose --env-file "${ENV_FILE}" -f "${COMPOSE_FILE}" up -d

echo "Restore completed."
