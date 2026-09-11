#!/usr/bin/env bash
set -euo pipefail

: "${HOST:=db}"
: "${PORT:=5432}"
: "${USER:=odoo}"
: "${PASSWORD:?PASSWORD is required}"
: "${ODOO_MASTER_PASSWORD:?ODOO_MASTER_PASSWORD is required}"
: "${ODOO_DB_NAME:=teq_trust}"
: "${ODOO_PROXY_MODE:=False}"
: "${ODOO_LIST_DB:=False}"
: "${ODOO_WORKERS:=0}"
: "${ODOO_LIMIT_TIME_CPU:=120}"
: "${ODOO_LIMIT_TIME_REAL:=240}"
: "${ODOO_MAX_CRON_THREADS:=1}"

CONFIG_FILE=/tmp/teq-odoo.conf

cat > "${CONFIG_FILE}" <<EOF
[options]
admin_passwd = ${ODOO_MASTER_PASSWORD}
db_host = ${HOST}
db_port = ${PORT}
db_user = ${USER}
db_password = ${PASSWORD}
db_name = ${ODOO_DB_NAME}
dbfilter = ^${ODOO_DB_NAME}$
list_db = ${ODOO_LIST_DB}
proxy_mode = ${ODOO_PROXY_MODE}
addons_path = /mnt/extra-addons,/usr/lib/python3/dist-packages/odoo/addons
data_dir = /var/lib/odoo
workers = ${ODOO_WORKERS}
limit_time_cpu = ${ODOO_LIMIT_TIME_CPU}
limit_time_real = ${ODOO_LIMIT_TIME_REAL}
max_cron_threads = ${ODOO_MAX_CRON_THREADS}
without_demo = all
EOF

exec /entrypoint.sh odoo -c "${CONFIG_FILE}" "$@"
