# Part of TEQ Trust Egypt for Quality.

from odoo import api, models, _
from odoo.exceptions import ValidationError


class TeqSignRequestUiSecurity(models.Model):
    _inherit = "teq.sign.request"

    @api.depends("requester_id", "signer_id")
    @api.depends_context("uid")
    def _compute_access_flags(self):
        is_manager = self.env.user.has_group("teq_trust_core.group_teq_sign_manager")
        for record in self:
            record.can_manage_sign = is_manager
            # A manager may administer the request, but must never impersonate
            # the person selected as signer.
            record.can_sign = record.signer_id == self.env.user
            record.can_requester_edit = is_manager or record.requester_id == self.env.user


class TeqEmployeeOnboardingValidation(models.TransientModel):
    _inherit = "teq.employee.onboarding"

    @api.constrains("name")
    def _check_employee_name(self):
        for wizard in self:
            if not (wizard.name or "").strip():
                raise ValidationError(_("Employee name cannot be blank."))
