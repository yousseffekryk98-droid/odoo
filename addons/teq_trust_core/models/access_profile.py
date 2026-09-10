# Part of TEQ Trust Egypt for Quality.

from odoo import api, fields, models, _
from odoo.exceptions import UserError


class TeqAccessProfile(models.Model):
    _name = "teq.access.profile"
    _description = "TEQ Access Profile"
    _order = "name"

    name = fields.Char(required=True, translate=True)
    active = fields.Boolean(default=True)
    description = fields.Text(translate=True)
    group_ids = fields.Many2many(
        "res.groups",
        "teq_access_profile_group_rel",
        "profile_id",
        "group_id",
        string="Odoo Access Groups",
        help="Odoo security groups granted when this profile is applied to a user.",
    )
    user_ids = fields.Many2many(
        "res.users",
        "teq_access_profile_user_rel",
        "profile_id",
        "user_id",
        string="Users",
        readonly=True,
    )

    def action_apply_to_users(self):
        self.ensure_one()
        if not self.env.user.has_group("teq_trust_core.group_teq_master_admin"):
            raise UserError(_("Only a TEQ Master Administrator can apply access profiles."))
        for user in self.user_ids:
            user._teq_apply_access_profiles()
        return True


class TeqAccessProfileMixin(models.AbstractModel):
    _name = "teq.access.profile.mixin"
    _description = "TEQ Access Profile Utilities"

    @api.model
    def _teq_select_highest_groups(self):
        """Return the highest-sequence group for each installed Odoo privilege.

        Odoo 19 groups that represent application access are linked to
        res.groups.privilege and ordered by sequence. Selecting the highest
        group per privilege gives the master administrator the strongest
        normal application access without bypassing Odoo ACLs/record rules.
        """
        Group = self.env["res.groups"].sudo()
        groups = Group.search([("privilege_id", "!=", False)])
        highest = {}
        for group in groups:
            privilege_id = group.privilege_id.id
            current = highest.get(privilege_id)
            if not current or group.sequence > current.sequence:
                highest[privilege_id] = group
        return Group.browse([group.id for group in highest.values()])
