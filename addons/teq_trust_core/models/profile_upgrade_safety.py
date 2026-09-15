# Part of TEQ Trust Egypt for Quality.

from odoo import api, models, _
from odoo.exceptions import UserError


class TeqAccessProfileUpgradeSafety(models.Model):
    _inherit = "teq.access.profile"

    @api.model
    def teq_seed_default_profiles(self):
        """Create missing standard profiles without resetting administrator edits."""
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
            "Inventory & Purchase Manager": ["stock.group_stock_manager", "purchase.group_purchase_manager"],
            "HR Officer": ["hr.group_hr_user"],
            "Human Resources Manager": ["hr.group_hr_manager", "hr_holidays.group_hr_holidays_manager", "hr_expense.group_hr_expense_manager", "teq_trust_core.group_teq_appraisal_manager"],
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
            if self.sudo().search([("name", "=", name)], limit=1):
                continue
            groups = full_groups if name == "TEQ Master Administrator" else helper._teq_existing_groups(xmlids)
            self.sudo().create({
                "name": name,
                "description": _("Preconfigured TEQ role profile. Combine profiles on a user when required."),
                "group_ids": [(6, 0, groups.ids)],
            })
        return True

    def action_restore_teq_default_profile(self):
        raise UserError(_("Automatic role reset is disabled to protect administrator customizations. Edit the role groups explicitly instead."))
