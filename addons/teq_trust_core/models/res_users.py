# Part of TEQ Trust Egypt for Quality.

from odoo import api, fields, models, _
from odoo.exceptions import UserError


class ResUsers(models.Model):
    _inherit = "res.users"

    teq_access_profile_ids = fields.Many2many(
        "teq.access.profile",
        "teq_access_profile_user_rel",
        "user_id",
        "profile_id",
        string="TEQ Roles / Access Profiles",
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

    @api.model_create_multi
    def create(self, vals_list):
        if any("teq_access_profile_ids" in values for values in vals_list):
            self._teq_check_master_admin()
        users = super().create(vals_list)
        users_to_apply = users.filtered("teq_access_profile_ids")
        if users_to_apply:
            users_to_apply._teq_apply_access_profiles()
        return users

    def write(self, values):
        profile_change = "teq_access_profile_ids" in values
        if profile_change:
            self._teq_check_master_admin()
        result = super().write(values)
        if profile_change:
            self._teq_apply_access_profiles()
        return result

    def action_teq_apply_access_profiles(self):
        return self._teq_apply_access_profiles()

    def action_teq_clear_managed_access(self):
        self._teq_check_master_admin()
        self.write({"teq_access_profile_ids": [(5, 0, 0)]})
        return True

    def action_teq_grant_full_access(self):
        self._teq_check_master_admin()
        helper = self.env["teq.access.profile.mixin"]
        highest_groups = helper._teq_select_highest_groups()
        system_group = self.env.ref("base.group_system")
        master_group = self.env.ref("teq_trust_core.group_teq_master_admin")
        target_groups = highest_groups | system_group | master_group
        for user in self:
            previous_groups = user.teq_managed_group_ids
            to_remove = previous_groups - target_groups
            commands = [(3, group.id) for group in to_remove]
            commands += [(4, group.id) for group in target_groups]
            user.sudo().write({
                "group_ids": commands,
                "teq_managed_group_ids": [(6, 0, target_groups.ids)],
            })
        return True
