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

cd "${ROOT_DIR}"
docker compose --env-file "${ENV_FILE}" -f "${COMPOSE_FILE}" exec -T db \
  pg_dump -U "${DB_USER}" -Fc "${DB_NAME}" > "${DB_FILE}"

docker compose --env-file "${ENV_FILE}" -f "${COMPOSE_FILE}" exec -T odoo \
  tar -C /var/lib/odoo -czf - filestore > "${FILESTORE_FILE}"

find "${BACKUP_DIR}" -type f -mtime +"${RETENTION}" -delete

echo "Database backup: ${DB_FILE}"
echo "Filestore backup: ${FILESTORE_FILE}"
