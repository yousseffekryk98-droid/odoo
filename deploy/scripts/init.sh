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
until docker compose --env-file "${ENV_FILE}" -f "${COMPOSE_FILE}" exec -T db \
  pg_isready -U "${DB_USER}" -d postgres >/dev/null 2>&1; do
  sleep 2
done

DB_EXISTS="$(docker compose --env-file "${ENV_FILE}" -f "${COMPOSE_FILE}" exec -T db \
  psql -U "${DB_USER}" -d postgres -tAc "SELECT 1 FROM pg_database WHERE datname='${DB_NAME}'")"

if [[ "${DB_EXISTS}" == "1" ]]; then
  echo "Database ${DB_NAME} already exists; skipping initialization."
else
  echo "Initializing ${DB_NAME} and installing TEQ Trust Egypt ERP..."
  docker compose --env-file "${ENV_FILE}" -f "${COMPOSE_FILE}" run --rm --no-deps odoo \
    -d "${DB_NAME}" -i teq_trust_core --without-demo=all --stop-after-init
fi

echo "Starting TEQ ERP..."
docker compose --env-file "${ENV_FILE}" -f "${COMPOSE_FILE}" up -d

echo "TEQ ERP is starting on port ${ODOO_PORT:-8069}."
echo "Check status with: docker compose --env-file deploy/.env -f docker-compose.teq.yml ps"
