from odoo import api, fields, models, _
from odoo.exceptions import UserError


class TeqSignRequest(models.Model):
    _name = "teq.sign.request"
    _description = "TEQ Signature Request"
    _inherit = ["mail.thread", "mail.activity.mixin"]
    _order = "id desc"

    name = fields.Char(default=lambda self: _("New"), readonly=True, copy=False, index=True)
    subject = fields.Char(required=True, tracking=True)
    document = fields.Binary(required=True, attachment=True)
    document_filename = fields.Char()
    requester_id = fields.Many2one("res.users", default=lambda self: self.env.user, required=True, tracking=True)
    signer_id = fields.Many2one("res.users", required=True, tracking=True, domain=[("share", "=", False)])
    state = fields.Selection([("draft", "Draft"), ("sent", "Waiting for Signature"), ("signed", "Signed"), ("refused", "Refused"), ("cancelled", "Cancelled")], default="draft", required=True, tracking=True)
    signature_image = fields.Binary(attachment=True, copy=False)
    signed_at = fields.Datetime(readonly=True, copy=False)
    refusal_reason = fields.Text(copy=False)
    notes = fields.Html()
    company_id = fields.Many2one("res.company", default=lambda self: self.env.company, required=True)

    @api.model_create_multi
    def create(self, vals_list):
        seq = self.env["ir.sequence"]
        for vals in vals_list:
            if vals.get("name", _("New")) == _("New"):
                vals["name"] = seq.next_by_code("teq.sign.request") or _("New")
        return super().create(vals_list)

    def action_send(self):
        for record in self:
            if not record.document:
                raise UserError(_("Upload the document before sending it for signature."))
            record.state = "sent"
            record.activity_schedule("mail.mail_activity_data_todo", user_id=record.signer_id.id, summary=_("Signature requested: %s") % record.subject)
        return True

    def action_sign(self):
        for record in self:
            if self.env.user != record.signer_id and not self.env.user.has_group("teq_trust_core.group_teq_sign_manager"):
                raise UserError(_("Only the assigned signer can sign this request."))
            if not record.signature_image:
                raise UserError(_("Add a signature image before signing."))
            record.write({"state": "signed", "signed_at": fields.Datetime.now()})
        return True

    def action_refuse(self):
        for record in self:
            if self.env.user != record.signer_id and not self.env.user.has_group("teq_trust_core.group_teq_sign_manager"):
                raise UserError(_("Only the assigned signer can refuse this request."))
            record.state = "refused"
        return True

    def action_cancel(self): self.write({"state": "cancelled"}); return True
    def action_reset_to_draft(self): self.write({"state": "draft", "signed_at": False}); return True
