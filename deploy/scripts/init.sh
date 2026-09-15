#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
ENV_FILE="${ROOT_DIR}/deploy/.env"
COMPOSE_FILE="${ROOT_DIR}/docker-compose.teq.yml"

if [[ ! -f "${ENV_FILE}" ]]; then
  echo "Missing ${ENV_FILE}." >&2
  echo "Copy deploy/env.example to deploy/.env and replace both CHANGE_ME passwords." >&2
  exit 1
fi

set -a
# shellcheck disable=SC1090
source "${ENV_FILE}"
set +a

if [[ "${POSTGRES_PASSWORD:-}" == CHANGE_ME* || "${ODOO_MASTER_PASSWORD:-}" == CHANGE_ME* ]]; then
  echo "Refusing to start with example passwords. Edit deploy/.env first." >&2
  exit 1
fi

DB_NAME="${ODOO_DB_NAME:-teq_trust}"
DB_USER="${POSTGRES_USER:-odoo}"

cd "${ROOT_DIR}"

echo "Starting PostgreSQL..."
docker compose --env-file "${ENV_FILE}" -f "${COMPOSE_FILE}" up -d db

echo "Waiting for PostgreSQL..."
DB_READY=0
for _attempt in $(seq 1 60); do
  if docker compose --env-file "${ENV_FILE}" -f "${COMPOSE_FILE}" exec -T db \
    pg_isready -U "${DB_USER}" -d postgres >/dev/null 2>&1; then
    DB_READY=1
    break
  fi
  sleep 2
done
if [[ "${DB_READY}" != "1" ]]; then
  echo "PostgreSQL did not become ready within 120 seconds." >&2
  exit 1
fi

# Never run module installation/upgrades concurrently with the normal Odoo service.
echo "Stopping the normal Odoo service before module install/upgrade..."
docker compose --env-file "${ENV_FILE}" -f "${COMPOSE_FILE}" stop odoo >/dev/null 2>&1 || true

DB_EXISTS="$(docker compose --env-file "${ENV_FILE}" -f "${COMPOSE_FILE}" exec -T db \
  psql -U "${DB_USER}" -d postgres -tAc "SELECT 1 FROM pg_database WHERE datname='${DB_NAME}'")"

if [[ "${DB_EXISTS}" == "1" ]]; then
  HAS_ODOO_SCHEMA="$(docker compose --env-file "${ENV_FILE}" -f "${COMPOSE_FILE}" exec -T db \
    psql -U "${DB_USER}" -d "${DB_NAME}" -tAc "SELECT CASE WHEN to_regclass('public.ir_module_module') IS NULL THEN 0 ELSE 1 END")"

  MODULE_STATE=""
  if [[ "${HAS_ODOO_SCHEMA}" == "1" ]]; then
    MODULE_STATE="$(docker compose --env-file "${ENV_FILE}" -f "${COMPOSE_FILE}" exec -T db \
      psql -U "${DB_USER}" -d "${DB_NAME}" -tAc "SELECT state FROM ir_module_module WHERE name='teq_trust_core' LIMIT 1")"
  fi

  if [[ "${MODULE_STATE}" == "installed" || "${MODULE_STATE}" == "to upgrade" ]]; then
    echo "Database ${DB_NAME} exists and TEQ is installed; upgrading teq_trust_core..."
    docker compose --env-file "${ENV_FILE}" -f "${COMPOSE_FILE}" run --rm --no-deps odoo \
      -d "${DB_NAME}" -u teq_trust_core --without-demo=all --stop-after-init
  else
    echo "Database ${DB_NAME} exists but TEQ is not installed; installing teq_trust_core..."
    docker compose --env-file "${ENV_FILE}" -f "${COMPOSE_FILE}" run --rm --no-deps odoo \
      -d "${DB_NAME}" -i teq_trust_core --without-demo=all --stop-after-init
  fi
else
  echo "Initializing ${DB_NAME} and installing TEQ Trust Egypt ERP..."
  docker compose --env-file "${ENV_FILE}" -f "${COMPOSE_FILE}" run --rm --no-deps odoo \
    -d "${DB_NAME}" -i teq_trust_core --without-demo=all --stop-after-init
fi

echo "Starting TEQ ERP..."
docker compose --env-file "${ENV_FILE}" -f "${COMPOSE_FILE}" up -d

echo "TEQ ERP is starting on port ${ODOO_PORT:-8069}."
echo "Check status with: docker compose --env-file deploy/.env -f docker-compose.teq.yml ps"
