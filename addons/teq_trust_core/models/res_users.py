# Part of TEQ Trust Egypt for Quality.

from odoo import fields, models, _
from odoo.exceptions import UserError


class ResUsers(models.Model):
    _inherit = "res.users"

    teq_access_profile_ids = fields.Many2many(
        "teq.access.profile",
        "teq_access_profile_user_rel",
        "user_id",
        "profile_id",
        string="TEQ Access Profiles",
        help="Reusable TEQ role bundles. Their Odoo groups are managed on this user.",
    )
    teq_managed_group_ids = fields.Many2many(
        "res.groups",
        "teq_user_managed_group_rel",
        "user_id",
        "group_id",
        string="TEQ Managed Groups",
        readonly=True,
        help="Groups currently controlled by TEQ access profiles for this user.",
    )

    def _teq_check_master_admin(self):
        if not self.env.user.has_group("teq_trust_core.group_teq_master_admin"):
            raise UserError(_("Only a TEQ Master Administrator can manage TEQ access profiles."))

    def _teq_profile_groups(self):
        self.ensure_one()
        return self.teq_access_profile_ids.filtered("active").mapped("group_ids")

    def _teq_apply_access_profiles(self):
        self._teq_check_master_admin()
        for user in self:
            target_groups = user._teq_profile_groups()
            previous_groups = user.teq_managed_group_ids
            to_remove = previous_groups - target_groups
            commands = [(3, group.id) for group in to_remove]
            commands += [(4, group.id) for group in target_groups]
            if commands:
                user.sudo().write({"group_ids": commands})
            user.sudo().write({"teq_managed_group_ids": [(6, 0, target_groups.ids)]})
        return True

    def action_teq_apply_access_profiles(self):
        return self._teq_apply_access_profiles()

    def action_teq_clear_managed_access(self):
        self._teq_check_master_admin()
        for user in self:
            commands = [(3, group.id) for group in user.teq_managed_group_ids]
            if commands:
                user.sudo().write({"group_ids": commands})
            user.sudo().write({"teq_managed_group_ids": [(5, 0, 0)]})
        return True

    def action_teq_grant_full_access(self):
        self._teq_check_master_admin()
        helper = self.env["teq.access.profile.mixin"]
        highest_groups = helper._teq_select_highest_groups()
        system_group = self.env.ref("base.group_system")
        master_group = self.env.ref("teq_trust_core.group_teq_master_admin")
        for user in self:
            commands = [(4, group.id) for group in highest_groups]
            commands += [(4, system_group.id), (4, master_group.id)]
            user.sudo().write({"group_ids": commands})
        return True
