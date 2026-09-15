# TEQ Trust Egypt for Quality ERP

This branch customizes the real Odoo 19.0 Community codebase for **TEQ Trust Egypt for Quality**.

## Install

Install the single application:

`TEQ Trust Egypt ERP` (`teq_trust_core`)

It installs the TEQ custom layer plus the available Odoo Community applications used by TEQ, including Sales, CRM, Point of Sale, Accounting/Invoicing, Expenses, Spreadsheet, Inventory, Purchase, Maintenance, Employees, Time Off, Fleet, Survey, Projects/Services, and their normal Odoo dependencies.

## TEQ administration

The **TEQ Administration** menu is the recommended starting point for administrators:

- **Onboard Employee** creates an HR employee and, when requested, an internal Odoo account in one flow.
- The onboarding flow accepts the login, initial password, work details, manager/department and one or more TEQ role bundles.
- **User Accounts & Passwords** opens internal Odoo users so administrators can archive/reactivate accounts, adjust roles and set/reset passwords.
- **Employees** opens the HR employee directory.
- **Roles & Access Profiles** manages reusable role bundles backed by normal Odoo security groups.
- **System Settings** opens Odoo configuration for the installed applications.
- TEQ role changes on a user are applied immediately; administrators no longer need to remember a second “apply” step.

## TEQ additions

- Master Administrator security role.
- Reusable TEQ access profiles that bundle normal Odoo security groups.
- Preconfigured employee/user, sales, invoicing, finance, inventory, purchase, HR, POS, project/service, calibration, sign, appraisal and ESG role profiles.
- Full-installed-app access action for trusted master administrators.
- Customer instrument / asset registry.
- TEQ reference standard registry and traceability.
- Calibration job workflow.
- Test points, nominal/measured values, deviation, uncertainty and tolerance checks.
- Quality review and certificate approval.
- PDF calibration certificates.
- Calibration due dates and automated activity reminders.
- Sales quotation and invoice links.
- Customer and Sales Order calibration smart buttons.
- TEQ internal document signature / approval application.
- TEQ employee appraisal application.
- TEQ ESG metric and target tracking.

## Security

TEQ access profiles do not bypass Odoo security. They apply normal Odoo `res.groups`, ACLs and record rules. The built-in administrator receives TEQ master access during module installation.

Employee onboarding and TEQ role administration are restricted to the TEQ Master Administrator group. Passwords are written through Odoo's normal user model and are not stored in the TEQ access-profile model.

The `19.0` branch remains unchanged.

## Enterprise-only Odoo applications

This repository is the Odoo Community fork. Proprietary Enterprise source is not copied into this public repository. Where requested features are not present in Community, this branch provides TEQ-owned functionality that can be replaced or integrated with licensed Enterprise modules later if required.
