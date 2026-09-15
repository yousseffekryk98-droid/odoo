from odoo import api, fields, models, _
from odoo.exceptions import UserError, ValidationError


class TeqHrAppraisal(models.Model):
    _name = "teq.hr.appraisal"
    _description = "TEQ Employee Appraisal"
    _inherit = ["mail.thread", "mail.activity.mixin"]
    _order = "review_date desc, id desc"

    name = fields.Char(compute="_compute_name", store=True)
    employee_id = fields.Many2one("hr.employee", required=True, tracking=True)
    manager_id = fields.Many2one("hr.employee", string="Appraisal Manager", tracking=True)
    review_date = fields.Date(default=fields.Date.context_today, required=True, tracking=True)
    period_from = fields.Date(required=True)
    period_to = fields.Date(required=True)
    state = fields.Selection(
        [
            ("draft", "Draft"),
            ("employee", "Employee Input"),
            ("manager", "Manager Review"),
            ("done", "Completed"),
            ("cancelled", "Cancelled"),
        ],
        default="draft",
        required=True,
        tracking=True,
    )
    objectives = fields.Html()
    employee_feedback = fields.Html()
    manager_feedback = fields.Html()
    development_plan = fields.Html()
    rating = fields.Selection(
        [
            ("1", "1 - Needs Improvement"),
            ("2", "2 - Developing"),
            ("3", "3 - Meets Expectations"),
            ("4", "4 - Exceeds Expectations"),
            ("5", "5 - Outstanding"),
        ],
        tracking=True,
    )
    company_id = fields.Many2one(related="employee_id.company_id", store=True, readonly=True)
    can_manage_appraisal = fields.Boolean(compute="_compute_access_flags")
    can_employee_edit = fields.Boolean(compute="_compute_access_flags")

    _APPRAISAL_FIELDS = {
        "employee_id",
        "manager_id",
        "review_date",
        "period_from",
        "period_to",
        "state",
        "objectives",
        "employee_feedback",
        "manager_feedback",
        "development_plan",
        "rating",
    }

    @api.depends("employee_id", "period_from", "period_to")
    def _compute_name(self):
        for record in self:
            record.name = _(
                "%(employee)s Appraisal (%(start)s - %(end)s)",
                employee=record.employee_id.name or _("Employee"),
                start=record.period_from or "",
                end=record.period_to or "",
            )

    @api.depends("employee_id", "state")
    @api.depends_context("uid")
    def _compute_access_flags(self):
        is_manager = self.env.user.has_group("teq_trust_core.group_teq_appraisal_manager")
        for record in self:
            record.can_manage_appraisal = is_manager
            record.can_employee_edit = (
                record.state == "employee"
                and record.employee_id.user_id == self.env.user
            )

    def _check_appraisal_manager(self):
        if not self.env.user.has_group("teq_trust_core.group_teq_appraisal_manager"):
            raise UserError(_("Only an Appraisal Manager can perform this action."))

    def _close_employee_input_activity(self, feedback):
        for record in self:
            employee_user = record.employee_id.user_id
            if not employee_user:
                continue
            activities = record.activity_ids.filtered(
                lambda activity: activity.active and activity.user_id == employee_user
            )
            if activities:
                activities.action_feedback(feedback=feedback)

    @api.onchange("employee_id")
    def _onchange_employee_id(self):
        if self.employee_id and self.employee_id.parent_id and not self.manager_id:
            self.manager_id = self.employee_id.parent_id

    def write(self, vals):
        if "state" in vals and not self.env.context.get("teq_appraisal_workflow_transition"):
            raise UserError(_("Use the appraisal workflow actions to change appraisal status."))

        is_manager = self.env.user.has_group("teq_trust_core.group_teq_appraisal_manager")
        for record in self:
            changed_business_fields = set(vals) & self._APPRAISAL_FIELDS
            if not changed_business_fields:
                continue
            if record.state in ("done", "cancelled") and not self.env.context.get("teq_appraisal_workflow_transition"):
                raise UserError(_("Completed or cancelled appraisals are locked."))
            if self.env.context.get("teq_appraisal_workflow_transition"):
                continue

            if is_manager:
                if "employee_feedback" in changed_business_fields:
                    raise UserError(_("Employee feedback can only be edited by the employee during Employee Input."))
                continue

            if record.employee_id.user_id != self.env.user:
                raise UserError(_("You can only edit your own appraisal feedback."))
            if record.state != "employee" or changed_business_fields - {"employee_feedback"}:
                raise UserError(_("During Employee Input you may edit only your own feedback."))
        return super().write(vals)

    @api.constrains("period_from", "period_to")
    def _check_period(self):
        for record in self:
            if record.period_from and record.period_to and record.period_from > record.period_to:
                raise ValidationError(_("Appraisal period start must be before the end date."))

    @api.constrains("employee_id", "manager_id")
    def _check_employee_manager_company(self):
        for record in self:
            if record.manager_id and record.manager_id.company_id != record.employee_id.company_id:
                raise ValidationError(_("The appraisal manager must belong to the employee company."))

    def action_employee_input(self):
        self._check_appraisal_manager()
        for record in self:
            if record.state != "draft":
                raise UserError(_("Only draft appraisals can request employee input."))
            if not record.employee_id.user_id:
                raise UserError(_("Link the employee to an Odoo user before requesting employee input."))
            record.with_context(teq_appraisal_workflow_transition=True).write({"state": "employee"})
            record.activity_schedule(
                "mail.mail_activity_data_todo",
                user_id=record.employee_id.user_id.id,
                date_deadline=record.review_date,
                summary=_("Appraisal input requested: %s") % record.display_name,
            )
        return True

    def action_manager_review(self):
        self._check_appraisal_manager()
        for record in self:
            if record.state != "employee":
                raise UserError(_("The appraisal must be in Employee Input before manager review."))
            record.with_context(teq_appraisal_workflow_transition=True).write({"state": "manager"})
            record._close_employee_input_activity(_("Employee input stage completed."))
        return True

    def action_complete(self):
        self._check_appraisal_manager()
        for record in self:
            if record.state != "manager":
                raise UserError(_("Only appraisals in Manager Review can be completed."))
            if not record.rating:
                raise UserError(_("Set an appraisal rating before completion."))
            if not record.manager_feedback:
                raise UserError(_("Add manager feedback before completing the appraisal."))
            record.with_context(teq_appraisal_workflow_transition=True).write({"state": "done"})
        return True

    def action_cancel(self):
        self._check_appraisal_manager()
        for record in self:
            if record.state in ("done", "cancelled"):
                raise UserError(_("Completed or already-cancelled appraisals cannot be cancelled."))
            record._close_employee_input_activity(_("Appraisal cancelled by a manager."))
            record.with_context(teq_appraisal_workflow_transition=True).write({"state": "cancelled"})
        return True

    def action_reset_to_draft(self):
        self._check_appraisal_manager()
        for record in self:
            if record.state != "cancelled":
                raise UserError(_("Only cancelled appraisals can be reset to draft."))
            record.with_context(teq_appraisal_workflow_transition=True).write({"state": "draft"})
        return True
