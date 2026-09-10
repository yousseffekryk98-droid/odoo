# TEQ Trust Egypt for Quality ERP

This branch customizes the real Odoo 19.0 Community codebase for **TEQ Trust Egypt for Quality**.

## Install

Install the single application:

`TEQ Trust Egypt ERP` (`teq_trust_core`)

It installs the TEQ custom layer plus the available Odoo Community applications used by TEQ, including Sales, CRM, Point of Sale, Accounting/Invoicing, Expenses, Spreadsheet, Inventory, Purchase, Maintenance, Employees, Time Off, Fleet, Survey, Projects/Services, and their normal Odoo dependencies.

## TEQ additions

- Master Administrator security role.
- Reusable TEQ access profiles that bundle normal Odoo security groups.
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

The `19.0` branch remains unchanged.

## Enterprise-only Odoo applications

This repository is the Odoo Community fork. Proprietary Enterprise source is not copied into this public repository. Where requested features are not present in Community, this branch provides TEQ-owned functionality that can be replaced or integrated with licensed Enterprise modules later if required.
