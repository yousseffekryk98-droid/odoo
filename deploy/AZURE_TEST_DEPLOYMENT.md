# Azure test deployment runbook

This runbook is for a temporary/shared TEQ Trust Egypt ERP acceptance-test environment.
Do not use it as a substitute for the production hardening checklist.

## Recommended shape

Use one Azure Linux VM for the test phase and run the repository's existing Docker Compose stack:

- Odoo 19 container
- PostgreSQL container
- persistent PostgreSQL named volume
- persistent Odoo data/filestore named volume

Keep PostgreSQL private. Only Odoo/reverse-proxy traffic should be reachable from the Internet.

## 1. Create the VM

Create an Ubuntu LTS VM with SSH-key authentication. For a multi-app Odoo acceptance test,
prefer enough memory to run Odoo, PostgreSQL, and the installed Community applications comfortably
rather than the smallest possible VM.

Network rules:

- SSH (22): restrict to administrator IP addresses.
- HTTPS (443): allow testers when a domain/reverse proxy is configured.
- HTTP (80): allow only when needed for certificate issuance/redirect.
- PostgreSQL (5432): do not expose publicly.
- Odoo (8069): keep private behind a reverse proxy where possible. For a short direct-IP test,
  restrict 8069 to approved tester IPs.

## 2. Install Docker

Install Docker Engine and Docker Compose v2 using the supported packages for the selected Ubuntu release.
Confirm:

```bash
docker --version
docker compose version
```

## 3. Clone the audited TEQ branch

After the audit PR is green and merged:

```bash
git clone --branch teq-trust-egypt-erp https://github.com/yousseffekryk98-droid/odoo.git
cd odoo
cp deploy/env.example deploy/.env
```

Edit `deploy/.env` and replace every example/default password with unique strong values.
Never commit `deploy/.env`.

For a reverse-proxy deployment, keep Odoo bound to localhost and enable proxy mode as documented
in `deploy/README.md`.

## 4. Initialize

```bash
bash deploy/scripts/init.sh
docker compose --env-file deploy/.env -f docker-compose.teq.yml ps
```

The initialization installs/upgrades `teq_trust_core` and its Odoo dependencies.

## 5. HTTPS for shared testing

Prefer a domain/subdomain pointed to the VM public IP and put Caddy, Nginx, or another maintained
reverse proxy in front of Odoo. Terminate TLS at the proxy and forward to Odoo on localhost:8069.

Do not share an unencrypted production-like login over plain HTTP.

## 6. Persistence

The Compose stack uses persistent named volumes for:

- PostgreSQL database files
- Odoo data directory / filestore

Normal container restarts, image updates, and `docker compose up -d` do not intentionally erase these
volumes. Do not run `docker compose down -v` on an environment whose data must be kept.

## 7. Backup and restore

Create a consistent TEQ backup:

```bash
bash deploy/scripts/backup.sh
```

The backup must include both the PostgreSQL database and matching Odoo filestore. Copy completed backup
archives off the VM (for example to protected Azure Blob Storage or another secured machine/account).

Test restore using the repository restore script before treating the environment as recoverable.

## 8. Updating the test server

After an audited change is merged:

```bash
git pull --ff-only
bash deploy/scripts/init.sh
```

Take a backup before meaningful upgrades.

## 9. Azure free-credit safety

Use the Azure Cost Management view to watch remaining credit and resource spend. A test environment
must have an off-VM backup before the free-account credit/period ends or before the VM is deleted.

When testers are not using the environment, deallocate compute if appropriate for the subscription,
while remembering that some attached resources can still have their own charges.

## Acceptance-test checklist

Before giving access to testers, verify:

- login page loads through HTTPS
- Master Administrator can access TEQ Administration
- create employee + Odoo login + initial password
- new employee can actually sign in
- assign/change/revoke TEQ roles
- user cannot access modules outside their roles
- company/department/job-position settings open correctly
- Sales, CRM, POS, Accounting, Expenses, Inventory, Purchase, Maintenance, HR, Time Off, Fleet,
  Survey, Projects/Services open
- Egyptian Accounting localization is installed
- calibration instrument/job/result/review/certificate workflow
- Sign signer/requester separation
- appraisal employee/manager separation
- ESG metric create/edit
- backup created and copied off-host
- restore rehearsal succeeds
