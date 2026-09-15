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

    @api.model
    def teq_seed_default_profiles(self):
        helper = self.env["teq.access.profile.mixin"]
        highest_groups = helper._teq_select_highest_groups()
        master_group = self.env.ref("teq_trust_core.group_teq_master_admin")
        system_group = self.env.ref("base.group_system")
        full_groups = highest_groups | master_group | system_group

        profiles = {
            "TEQ Master Administrator": [],
            "General Internal User": ["base.group_user"],
            "Calibration Technician": ["teq_trust_core.group_teq_calibration_user"],
            "Calibration & Quality Manager": ["teq_trust_core.group_teq_calibration_manager"],
            "Sales User - Own Documents": ["sales_team.group_sale_salesman"],
            "Sales User - All Documents": ["sales_team.group_sale_salesman_all_leads"],
            "Sales & CRM Manager": ["sales_team.group_sale_manager"],
            "Invoicing / Billing User": ["account.group_account_invoice"],
            "Accounting Read-only / Auditor": ["account.group_account_readonly"],
            "Finance Manager": ["account.group_account_manager"],
            "Inventory User": ["stock.group_stock_user"],
            "Purchase User": ["purchase.group_purchase_user"],
            "Inventory & Purchase Manager": [
                "stock.group_stock_manager",
                "purchase.group_purchase_manager",
            ],
            "HR Officer": ["hr.group_hr_user"],
            "Human Resources Manager": [
                "hr.group_hr_manager",
                "hr_holidays.group_hr_holidays_manager",
                "hr_expense.group_hr_expense_manager",
                "teq_trust_core.group_teq_appraisal_manager",
            ],
            "Time Off Officer": ["hr_holidays.group_hr_holidays_user"],
            "Time Off Manager": ["hr_holidays.group_hr_holidays_manager"],
            "Expense Team Approver": ["hr_expense.group_hr_expense_team_approver"],
            "Expense All Approver": ["hr_expense.group_hr_expense_user"],
            "Expense Manager": ["hr_expense.group_hr_expense_manager"],
            "Fleet Officer": ["fleet.fleet_group_user"],
            "Fleet Manager": ["fleet.fleet_group_manager"],
            "Maintenance Equipment Manager": ["maintenance.group_equipment_manager"],
            "Survey User": ["survey.group_survey_user"],
            "Survey Manager": ["survey.group_survey_manager"],
            "Point of Sale User": ["point_of_sale.group_pos_user"],
            "Point of Sale Manager": ["point_of_sale.group_pos_manager"],
            "Projects & Services User": ["project.group_project_user"],
            "Projects & Services Manager": ["project.group_project_manager"],
            "Document Sign User": ["teq_trust_core.group_teq_sign_user"],
            "Document Sign Manager": ["teq_trust_core.group_teq_sign_manager"],
            "Appraisal Employee": ["teq_trust_core.group_teq_appraisal_user"],
            "Appraisal Manager": ["teq_trust_core.group_teq_appraisal_manager"],
            "ESG User": ["teq_trust_core.group_teq_esg_user"],
            "ESG Manager": ["teq_trust_core.group_teq_esg_manager"],
        }

        for name, xmlids in profiles.items():
            groups = full_groups if name == "TEQ Master Administrator" else helper._teq_existing_groups(xmlids)
            profile = self.sudo().search([("name", "=", name)], limit=1)
            values = {
                "name": name,
                "description": "Preconfigured TEQ role profile. Combine profiles on a user when required.",
                "group_ids": [(6, 0, groups.ids)],
            }
            if profile:
                profile.write(values)
            else:
                self.sudo().create(values)
        return True


class TeqAccessProfileMixin(models.AbstractModel):
    _name = "teq.access.profile.mixin"
    _description = "TEQ Access Profile Utilities"

    @api.model
    def _teq_existing_groups(self, xmlids):
        groups = self.env["res.groups"]
        for xmlid in xmlids:
            group = self.env.ref(xmlid, raise_if_not_found=False)
            if group and group._name == "res.groups":
                groups |= group
        return groups

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
