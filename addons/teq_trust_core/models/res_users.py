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
        help="Reusable TEQ role bundles. Their Odoo groups are added to this user.",
    )

    def _teq_check_master_admin(self):
        if not self.env.user.has_group("teq_trust_core.group_teq_master_admin"):
            raise UserError(_("Only a TEQ Master Administrator can manage TEQ access profiles."))

    def _teq_profile_groups(self):
        self.ensure_one()
        return self.teq_access_profile_ids.mapped("group_ids")

    def _teq_apply_access_profiles(self):
        self._teq_check_master_admin()
        for user in self:
            profile_groups = user._teq_profile_groups()
            if profile_groups:
                user.sudo().write({"group_ids": [(4, group.id) for group in profile_groups]})
        return True

    def action_teq_apply_access_profiles(self):
        return self._teq_apply_access_profiles()

    def action_teq_grant_full_access(self):
        self._teq_check_master_admin()
        helper = self.env["teq.access.profile.mixin"]
        highest_groups = helper._teq_select_highest_groups()
        for user in self:
            commands = [(4, group.id) for group in highest_groups]
            commands.append((4, self.env.ref("base.group_system").id))
            user.sudo().write({"group_ids": commands})
        return True
