#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
ENV_FILE="${ROOT_DIR}/deploy/.env"
COMPOSE_FILE="${ROOT_DIR}/docker-compose.teq.yml"

if [[ ! -f "${ENV_FILE}" ]]; then
  echo "Missing ${ENV_FILE}. Copy deploy/env.example to deploy/.env first." >&2
  exit 1
fi

set -a
# shellcheck disable=SC1090
source "${ENV_FILE}"
set +a

DB_USER="${POSTGRES_USER:-odoo}"
TEST_DB="teq_test_$(date +%Y%m%d%H%M%S)_$$"

cd "${ROOT_DIR}"
docker compose --env-file "${ENV_FILE}" -f "${COMPOSE_FILE}" up -d db >/dev/null

for _attempt in $(seq 1 30); do
  if docker compose --env-file "${ENV_FILE}" -f "${COMPOSE_FILE}" exec -T db \
    pg_isready -U "${DB_USER}" -d postgres >/dev/null 2>&1; then
    break
  fi
  if [[ "${_attempt}" == "30" ]]; then
    echo "PostgreSQL did not become ready for tests." >&2
    exit 1
  fi
  sleep 2
done

cleanup() {
  docker compose --env-file "${ENV_FILE}" -f "${COMPOSE_FILE}" exec -T db \
    dropdb -U "${DB_USER}" --if-exists "${TEST_DB}" >/dev/null 2>&1 || true
  docker compose --env-file "${ENV_FILE}" -f "${COMPOSE_FILE}" run -T --rm --no-deps \
    --entrypoint /bin/bash odoo -c "rm -rf '/var/lib/odoo/filestore/${TEST_DB}'" >/dev/null 2>&1 || true
}
trap cleanup EXIT

echo "Running TEQ Odoo tests in temporary database ${TEST_DB}..."
docker compose --env-file "${ENV_FILE}" -f "${COMPOSE_FILE}" run --rm --no-deps \
  -e "ODOO_DB_NAME=${TEST_DB}" odoo \
  -d "${TEST_DB}" -i teq_trust_core --without-demo=all \
  --test-enable --test-tags /teq_trust_core --stop-after-init

echo "TEQ Odoo tests passed. Temporary database will now be removed."
