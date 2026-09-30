from odoo.exceptions import AccessError, ValidationError
from odoo.tests import tagged
from odoo.tests.common import TransactionCase


@tagged("post_install", "-at_install")
class TestTeqEmployeeOnboarding(TransactionCase):

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.admin = cls.env.ref("base.user_admin")
        cls.internal_group = cls.env.ref("base.group_user")
        cls.profile = cls.env["teq.access.profile"].create({
            "name": "Test Internal User",
            "group_ids": [(6, 0, [cls.internal_group.id])],
        })

    def test_master_admin_can_create_employee_user_with_role(self):
        example_password = "A" * 12
        wizard = self.env["teq.employee.onboarding"].with_user(self.admin).create({
            "name": "TEQ Test Employee",
            "create_login": True,
            "login": "teq.test.employee@example.com",
            "email": "teq.test.employee@example.com",
            "initial_password": example_password,
            "confirm_password": example_password,
            "access_profile_ids": [(6, 0, [self.profile.id])],
        })
        wizard.action_create_employee()

        user = self.env["res.users"].with_context(active_test=False).search([
            ("login", "=", "teq.test.employee@example.com"),
        ], limit=1)
        self.assertTrue(user)
        self.assertTrue(user.employee_id)
        self.assertIn(self.profile, user.teq_access_profile_ids)
        self.assertIn(self.internal_group, user.group_ids)

        auth_info = user.with_user(user)._check_credentials(
            {"type": "password", "password": example_password},
            {"interactive": True},
        )
        self.assertEqual(auth_info["uid"], user.id)

    def test_onboarding_rejects_blank_name(self):
        with self.assertRaises(ValidationError):
            self.env["teq.employee.onboarding"].with_user(self.admin).create({
                "name": "   ",
                "create_login": False,
            })

    def test_onboarding_rejects_password_mismatch(self):
        with self.assertRaises(ValidationError):
            self.env["teq.employee.onboarding"].with_user(self.admin).create({
                "name": "Password Validation User",
                "create_login": True,
                "login": "teq.password.validation@example.com",
                "initial_password": "StrongPass123",
                "confirm_password": "DifferentPass123",
            })

    def test_administration_actions_are_available(self):
        expected_actions = {
            "teq_trust_core.action_teq_employee_onboarding": "teq.employee.onboarding",
            "teq_trust_core.action_teq_user_accounts": "res.users",
            "teq_trust_core.action_teq_employees": "hr.employee",
            "teq_trust_core.action_teq_access_profile": "teq.access.profile",
            "teq_trust_core.action_teq_system_settings": "res.config.settings",
            "teq_trust_core.action_teq_departments": "hr.department",
            "teq_trust_core.action_teq_job_positions": "hr.job",
            "teq_trust_core.action_teq_companies": "res.company",
        }
        for xmlid, res_model in expected_actions.items():
            action = self.env.ref(xmlid)
            self.assertEqual(action.res_model, res_model, xmlid)

    def test_non_master_cannot_open_onboarding(self):
        ordinary = self.env["res.users"].with_user(self.admin).create({
            "name": "Ordinary User",
            "login": "ordinary.teq@example.com",
            "email": "ordinary.teq@example.com",
            "group_ids": [(6, 0, [self.internal_group.id])],
        })
        with self.assertRaises(AccessError):
            self.env["teq.employee.onboarding"].with_user(ordinary).create({
                "name": "Blocked Employee",
                "create_login": False,
            })
