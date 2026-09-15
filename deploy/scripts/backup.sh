#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
ENV_FILE="${ROOT_DIR}/deploy/.env"
COMPOSE_FILE="${ROOT_DIR}/docker-compose.teq.yml"
BACKUP_DIR="${ROOT_DIR}/deploy/backups"

if [[ ! -f "${ENV_FILE}" ]]; then
  echo "Missing ${ENV_FILE}. Copy deploy/env.example to deploy/.env first." >&2
  exit 1
fi

set -a
# shellcheck disable=SC1090
source "${ENV_FILE}"
set +a

mkdir -p "${BACKUP_DIR}"
STAMP="$(date +%Y%m%d_%H%M%S)"
DB_NAME="${ODOO_DB_NAME:-teq_trust}"
DB_USER="${POSTGRES_USER:-odoo}"
RETENTION="${BACKUP_RETENTION_DAYS:-14}"
DB_FILE="${BACKUP_DIR}/${DB_NAME}_${STAMP}.dump"
FILESTORE_FILE="${BACKUP_DIR}/${DB_NAME}_${STAMP}_filestore.tar.gz"
DB_TMP="${DB_FILE}.partial"
FILESTORE_TMP="${FILESTORE_FILE}.partial"

cd "${ROOT_DIR}"

docker compose --env-file "${ENV_FILE}" -f "${COMPOSE_FILE}" up -d db >/dev/null
for _attempt in $(seq 1 30); do
  if docker compose --env-file "${ENV_FILE}" -f "${COMPOSE_FILE}" exec -T db \
    pg_isready -U "${DB_USER}" -d "${DB_NAME}" >/dev/null 2>&1; then
    break
  fi
  if [[ "${_attempt}" == "30" ]]; then
    echo "PostgreSQL did not become ready for backup." >&2
    exit 1
  fi
  sleep 2
done

WAS_RUNNING=0
if [[ -n "$(docker compose --env-file "${ENV_FILE}" -f "${COMPOSE_FILE}" ps --status running -q odoo 2>/dev/null)" ]]; then
  WAS_RUNNING=1
  echo "Stopping Odoo briefly to create a consistent database + filestore backup..."
  docker compose --env-file "${ENV_FILE}" -f "${COMPOSE_FILE}" stop odoo >/dev/null
fi

cleanup() {
  rm -f "${DB_TMP}" "${FILESTORE_TMP}"
  if [[ "${WAS_RUNNING}" == "1" ]]; then
    docker compose --env-file "${ENV_FILE}" -f "${COMPOSE_FILE}" up -d odoo >/dev/null || true
  fi
}
trap cleanup EXIT

docker compose --env-file "${ENV_FILE}" -f "${COMPOSE_FILE}" exec -T db \
  pg_dump -U "${DB_USER}" -Fc "${DB_NAME}" > "${DB_TMP}"

docker compose --env-file "${ENV_FILE}" -f "${COMPOSE_FILE}" run -T --rm --no-deps \
  --entrypoint /bin/bash odoo -c \
  "cd /var/lib/odoo && if [ -d 'filestore/${DB_NAME}' ]; then tar -czf - 'filestore/${DB_NAME}'; else tar -czf - --files-from /dev/null; fi" \
  > "${FILESTORE_TMP}"

mv "${DB_TMP}" "${DB_FILE}"
mv "${FILESTORE_TMP}" "${FILESTORE_FILE}"
find "${BACKUP_DIR}" -type f -mtime +"${RETENTION}" -delete

echo "Database backup: ${DB_FILE}"
echo "Filestore backup: ${FILESTORE_FILE}"
