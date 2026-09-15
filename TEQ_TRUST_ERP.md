# TEQ Trust Egypt for Quality ERP

This branch customizes the real Odoo 19.0 Community codebase for **TEQ Trust Egypt for Quality**. The upstream `19.0` branch remains unchanged.

## Install

Install the single application:

`TEQ Trust Egypt ERP` (`teq_trust_core`)

It installs the TEQ custom layer plus the available Odoo Community applications used by TEQ, including Sales, CRM, Point of Sale, Accounting/Invoicing, Expenses, Spreadsheet, Inventory, Purchase, Maintenance, Employees, Time Off, Fleet, Survey, Projects/Services, and their normal Odoo dependencies.

## TEQ administration

The **TEQ Administration** menu is the recommended starting point for administrators:

- **Onboard Employee** creates an HR employee and, when requested, an internal Odoo account in one flow.
- The onboarding flow accepts the login, initial password, work details, company, manager/department and one or more TEQ role bundles.
- **User Accounts & Passwords** opens internal Odoo users so administrators can archive/reactivate accounts, adjust roles and set/reset passwords.
- **Employees** opens the HR employee directory.
- **Roles & Access Profiles** manages reusable role bundles backed by normal Odoo security groups.
- **System Settings** opens Odoo configuration for the installed applications.
- TEQ role changes and access-profile permission changes are propagated immediately to assigned users.
- The current Master Administrator is protected from accidentally removing their own TEQ/Odoo administration access.

## TEQ additions

- Master Administrator security role.
- Reusable TEQ access profiles that bundle normal Odoo security groups.
- Preconfigured employee/user, sales, invoicing, finance/auditor, inventory, purchase, HR, time-off, expenses, fleet, maintenance, survey, POS, project/service, calibration, sign, appraisal and ESG role profiles.
- Full-installed-app access action for trusted master administrators.
- Customer instrument / asset registry.
- TEQ reference standard registry and traceability.
- Calibration job workflow with technician assignment and quality-manager approval separation.
- Test points, nominal/measured values, deviation, uncertainty and tolerance checks.
- Quality review and controlled certificate approval/voiding.
- Approved calibration certificates become immutable; replacements require a new certificate after voiding the old one.
- PDF calibration certificates with draft/void markings and traceability details.
- Calibration due dates and automated activity reminders.
- Sales quotation and invoice links.
- Customer and Sales Order calibration smart buttons.
- TEQ internal document signature / approval workflow with signer/requester separation and signed-document immutability.
- TEQ employee appraisal workflow with employee self-feedback separated from manager rating/review fields.
- TEQ ESG metric tracking supporting both higher-is-better and lower-is-better targets, including explicit zero targets.

## Security and audit controls

TEQ access profiles do not bypass Odoo security. They apply normal Odoo `res.groups`, ACLs and record rules.

The custom TEQ models enforce company boundaries through record rules. Calibration job/result access is restricted by assignment, while calibration approval and certificate control require the TEQ Calibration & Quality Manager role. UI button visibility is not treated as authorization; the corresponding Python workflow methods enforce the same permissions server-side.

Employee onboarding and TEQ role administration are restricted to the TEQ Master Administrator group. Passwords are handled by Odoo's normal `res.users` authentication model and are not stored in the TEQ access-profile model.

Signature requests lock controlled document fields after sending and become immutable after signature. Appraisal employees may change only their own self-feedback during the Employee Input stage; rating and manager feedback remain manager-controlled.

## Testing

Run the isolated TEQ test suite with:

```bash
bash deploy/scripts/test.sh
```

The script creates a temporary Odoo database, installs `teq_trust_core`, runs the module tests, and removes the temporary database and filestore afterward. It does not test against or modify the production `teq_trust` database.

The branch also contains `.github/workflows/teq-core-tests.yml`, which runs the same isolated module tests on pushes to `teq-trust-egypt-erp`.

## Enterprise-only Odoo applications

This repository is the Odoo Community fork. Proprietary Enterprise source is not copied into this public repository. Where requested features are not present in Community, this branch provides TEQ-owned functionality that can be replaced or integrated with licensed Enterprise modules later if required.
