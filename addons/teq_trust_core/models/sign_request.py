from odoo import api, fields, models, _
from odoo.exceptions import UserError, ValidationError


class TeqSignRequest(models.Model):
    _name = "teq.sign.request"
    _description = "TEQ Signature Request"
    _inherit = ["mail.thread", "mail.activity.mixin"]
    _order = "id desc"

    name = fields.Char(default=lambda self: _("New"), readonly=True, copy=False, index=True)
    subject = fields.Char(required=True, tracking=True)
    document = fields.Binary(required=True, attachment=True)
    document_filename = fields.Char()
    requester_id = fields.Many2one(
        "res.users",
        default=lambda self: self.env.user,
        required=True,
        tracking=True,
    )
    signer_id = fields.Many2one(
        "res.users",
        required=True,
        tracking=True,
        domain="[('share', '=', False), ('company_ids', 'in', company_id)]",
    )
    state = fields.Selection(
        [
            ("draft", "Draft"),
            ("sent", "Waiting for Signature"),
            ("signed", "Signed"),
            ("refused", "Refused"),
            ("cancelled", "Cancelled"),
        ],
        default="draft",
        required=True,
        tracking=True,
    )
    signature_image = fields.Binary(attachment=True, copy=False)
    signed_at = fields.Datetime(readonly=True, copy=False)
    refusal_reason = fields.Text(copy=False)
    notes = fields.Html()
    company_id = fields.Many2one("res.company", default=lambda self: self.env.company, required=True)
    can_manage_sign = fields.Boolean(compute="_compute_access_flags")
    can_sign = fields.Boolean(compute="_compute_access_flags")
    can_requester_edit = fields.Boolean(compute="_compute_access_flags")

    _REQUESTER_DRAFT_FIELDS = {
        "subject",
        "document",
        "document_filename",
        "signer_id",
        "notes",
        "company_id",
    }
    _SIGNER_SENT_FIELDS = {"signature_image", "refusal_reason"}
    _CONTROLLED_FIELDS = _REQUESTER_DRAFT_FIELDS | _SIGNER_SENT_FIELDS | {"requester_id"}

    @api.depends("requester_id", "signer_id")
    @api.depends_context("uid")
    def _compute_access_flags(self):
        is_manager = self.env.user.has_group("teq_trust_core.group_teq_sign_manager")
        for record in self:
            record.can_manage_sign = is_manager
            record.can_sign = is_manager or record.signer_id == self.env.user
            record.can_requester_edit = is_manager or record.requester_id == self.env.user

    def _check_sign_manager(self):
        if not self.env.user.has_group("teq_trust_core.group_teq_sign_manager"):
            raise UserError(_("Only a Document Sign Manager can perform this action."))

    def _check_requester_or_manager(self):
        if self.env.user.has_group("teq_trust_core.group_teq_sign_manager"):
            return
        for record in self:
            if record.requester_id != self.env.user:
                raise UserError(_("Only the requester can perform this action."))

    def _check_signer_or_manager(self):
        if self.env.user.has_group("teq_trust_core.group_teq_sign_manager"):
            return
        for record in self:
            if record.signer_id != self.env.user:
                raise UserError(_("Only the assigned signer can perform this action."))

    def _close_signature_activities(self, feedback):
        for record in self:
            activities = record.activity_ids.filtered(
                lambda activity: activity.active and activity.user_id == record.signer_id
            )
            if activities:
                activities.action_feedback(feedback=feedback)

    @api.model_create_multi
    def create(self, vals_list):
        is_manager = self.env.user.has_group("teq_trust_core.group_teq_sign_manager")
        seq = self.env["ir.sequence"]
        for vals in vals_list:
            if vals.get("name", _("New")) == _("New"):
                vals["name"] = seq.next_by_code("teq.sign.request") or _("New")
            if not is_manager:
                vals["requester_id"] = self.env.user.id
        return super().create(vals_list)

    def write(self, vals):
        if "state" in vals and not self.env.context.get("teq_sign_workflow_transition"):
            raise UserError(_("Use the signature workflow actions to change request status."))

        is_manager = self.env.user.has_group("teq_trust_core.group_teq_sign_manager")
        for record in self:
            if self.env.context.get("teq_sign_workflow_transition"):
                continue

            allowed_fields = set()
            if record.state == "draft" and (is_manager or record.requester_id == self.env.user):
                allowed_fields |= self._REQUESTER_DRAFT_FIELDS
                if is_manager:
                    allowed_fields.add("requester_id")
            if record.state == "sent" and (is_manager or record.signer_id == self.env.user):
                allowed_fields |= self._SIGNER_SENT_FIELDS

            restricted = (set(vals) & self._CONTROLLED_FIELDS) - allowed_fields
            if restricted:
                if record.state == "signed":
                    raise UserError(
                        _("A signed request is immutable. Create a new request for a revised document.")
                    )
                raise UserError(
                    _("You cannot edit these document-sign fields at the current workflow stage.")
                )

        return super().write(vals)

    @api.constrains("company_id", "requester_id", "signer_id")
    def _check_company_access(self):
        for record in self:
            if record.company_id not in record.requester_id.company_ids:
                raise ValidationError(_("The requester must have access to the signature-request company."))
            if record.company_id not in record.signer_id.company_ids:
                raise ValidationError(_("The signer must have access to the signature-request company."))

    def action_send(self):
        self._check_requester_or_manager()
        for record in self:
            if record.state != "draft":
                raise UserError(_("Only draft requests can be sent for signature."))
            if not record.document:
                raise UserError(_("Upload the document before sending it for signature."))
            if not record.signer_id:
                raise UserError(_("Choose a signer before sending the request."))
            record.with_context(teq_sign_workflow_transition=True).write({"state": "sent"})
            record.activity_schedule(
                "mail.mail_activity_data_todo",
                user_id=record.signer_id.id,
                summary=_("Signature requested: %s") % record.subject,
            )
        return True

    def action_sign(self):
        self._check_signer_or_manager()
        for record in self:
            if record.state != "sent":
                raise UserError(_("Only requests waiting for signature can be signed."))
            if not record.signature_image:
                raise UserError(_("Add a signature image before signing."))
            record.with_context(teq_sign_workflow_transition=True).write(
                {"state": "signed", "signed_at": fields.Datetime.now()}
            )
            record._close_signature_activities(_("Document signed."))
        return True

    def action_refuse(self):
        self._check_signer_or_manager()
        for record in self:
            if record.state != "sent":
                raise UserError(_("Only requests waiting for signature can be refused."))
            if not (record.refusal_reason or "").strip():
                raise UserError(_("Enter a refusal reason before refusing the request."))
            record.with_context(teq_sign_workflow_transition=True).write({"state": "refused"})
            record._close_signature_activities(_("Signature request refused."))
        return True

    def action_cancel(self):
        self._check_requester_or_manager()
        for record in self:
            if record.state in ("signed", "cancelled"):
                raise UserError(_("Signed or already-cancelled requests cannot be cancelled."))
            record.with_context(teq_sign_workflow_transition=True).write({"state": "cancelled"})
            record._close_signature_activities(_("Signature request cancelled."))
        return True

    def action_reset_to_draft(self):
        self._check_sign_manager()
        for record in self:
            if record.state not in ("refused", "cancelled"):
                raise UserError(_("Only refused or cancelled requests can be reset to draft."))
            record._close_signature_activities(_("Signature request reset by a manager."))
            record.with_context(teq_sign_workflow_transition=True).write(
                {
                    "state": "draft",
                    "signature_image": False,
                    "signed_at": False,
                    "refusal_reason": False,
                }
            )
        return True
