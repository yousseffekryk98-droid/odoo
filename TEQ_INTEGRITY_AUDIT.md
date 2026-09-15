# TEQ ERP integrity audit

This note tracks the September 2026 hardening pass performed after the user-management upgrade.

The audit reviews the TEQ delta against Odoo 19.0 rather than modifying unchanged upstream Odoo source. The custom module now enforces workflow transitions server-side, protects signer identity, fingerprints documents at send time, locks calibration identity/results at controlled stages, validates customer/contact/reference-standard relationships, validates ESG company responsibility, and adds practical search filters for daily use.

Operational rule: upgrade `teq_trust_core` after pulling this branch and run the TEQ test suite before production rollout.
