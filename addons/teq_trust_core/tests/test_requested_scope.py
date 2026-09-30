from odoo.tests import tagged
from odoo.tests.common import TransactionCase


@tagged("post_install", "-at_install")
class TestTeqRequestedScope(TransactionCase):

    def test_required_community_apps_are_installed(self):
        required_modules = {
            "sale_management",
            "crm",
            "point_of_sale",
            "account",
            "l10n_eg",
            "hr_expense",
            "spreadsheet",
            "stock",
            "purchase",
            "maintenance",
            "hr",
            "hr_holidays",
            "fleet",
            "survey",
            "project",
        }
        modules = self.env["ir.module.module"].sudo().search([
            ("name", "in", sorted(required_modules)),
        ])
        installed = set(modules.filtered(lambda module: module.state == "installed").mapped("name"))
        self.assertEqual(required_modules - installed, set())

    def test_required_teq_models_are_registered(self):
        required_models = {
            "teq.access.profile",
            "teq.employee.onboarding",
            "teq.calibration.equipment",
            "teq.calibration.job",
            "teq.calibration.result.line",
            "teq.calibration.certificate",
            "teq.sign.request",
            "teq.hr.appraisal",
            "teq.esg.metric",
        }
        self.assertEqual(
            {model for model in required_models if model not in self.env.registry},
            set(),
        )

    def test_standard_teq_role_profiles_exist(self):
        required_profiles = {
            "TEQ Master Administrator",
            "General Internal User",
            "Calibration Technician",
            "Calibration & Quality Manager",
            "Sales User - Own Documents",
            "Sales User - All Documents",
            "Sales & CRM Manager",
            "Invoicing / Billing User",
            "Accounting Read-only / Auditor",
            "Finance Manager",
            "Inventory User",
            "Purchase User",
            "Inventory & Purchase Manager",
            "HR Officer",
            "Human Resources Manager",
            "Time Off Officer",
            "Time Off Manager",
            "Expense Team Approver",
            "Expense All Approver",
            "Expense Manager",
            "Fleet Officer",
            "Fleet Manager",
            "Maintenance Equipment Manager",
            "Survey User",
            "Survey Manager",
            "Point of Sale User",
            "Point of Sale Manager",
            "Projects & Services User",
            "Projects & Services Manager",
            "Document Sign User",
            "Document Sign Manager",
            "Appraisal Employee",
            "Appraisal Manager",
            "ESG User",
            "ESG Manager",
        }
        profiles = self.env["teq.access.profile"].sudo().search([
            ("name", "in", sorted(required_profiles)),
        ])
        self.assertEqual(required_profiles - set(profiles.mapped("name")), set())

    def test_master_admin_has_settings_access(self):
        admin = self.env.ref("base.user_admin")
        self.assertTrue(admin.has_group("teq_trust_core.group_teq_master_admin"))
        self.assertTrue(admin.has_group("base.group_system"))
