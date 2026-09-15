# Part of TEQ Trust Egypt for Quality.

from odoo.tests import tagged
from odoo.tests.common import TransactionCase


@tagged("post_install", "-at_install")
class TestTeqProfileUpgradeSafety(TransactionCase):

    def test_seed_does_not_overwrite_existing_profile_customization(self):
        admin = self.env.ref("base.user_admin")
        profile = self.env["teq.access.profile"].with_user(admin).search([
            ("name", "=", "General Internal User"),
        ], limit=1)
        self.assertTrue(profile)
        sign_group = self.env.ref("teq_trust_core.group_teq_sign_user")
        profile.with_user(admin).write({"group_ids": [(6, 0, [sign_group.id])]})
        self.env["teq.access.profile"].with_user(admin).teq_seed_default_profiles()
        self.assertEqual(profile.group_ids, sign_group)
