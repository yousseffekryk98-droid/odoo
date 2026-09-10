from odoo import api, fields, models, _
from odoo.exceptions import ValidationError


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
    state = fields.Selection([("draft", "Draft"), ("employee", "Employee Input"), ("manager", "Manager Review"), ("done", "Completed"), ("cancelled", "Cancelled")], default="draft", required=True, tracking=True)
    objectives = fields.Html()
    employee_feedback = fields.Html()
    manager_feedback = fields.Html()
    development_plan = fields.Html()
    rating = fields.Selection([("1", "1 - Needs Improvement"), ("2", "2 - Developing"), ("3", "3 - Meets Expectations"), ("4", "4 - Exceeds Expectations"), ("5", "5 - Outstanding")], tracking=True)
    company_id = fields.Many2one(related="employee_id.company_id", store=True, readonly=True)

    @api.depends("employee_id", "period_from", "period_to")
    def _compute_name(self):
        for record in self:
            record.name = _("%(employee)s Appraisal (%(start)s - %(end)s)", employee=record.employee_id.name or _("Employee"), start=record.period_from or "", end=record.period_to or "")

    @api.constrains("period_from", "period_to")
    def _check_period(self):
        for record in self:
            if record.period_from and record.period_to and record.period_from > record.period_to:
                raise ValidationError(_("Appraisal period start must be before the end date."))

    def action_employee_input(self): self.write({"state": "employee"}); return True
    def action_manager_review(self): self.write({"state": "manager"}); return True
    def action_complete(self): self.write({"state": "done"}); return True
    def action_cancel(self): self.write({"state": "cancelled"}); return True
    def action_reset_to_draft(self): self.write({"state": "draft"}); return True
