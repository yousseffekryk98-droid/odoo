from odoo.exceptions import AccessError
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
