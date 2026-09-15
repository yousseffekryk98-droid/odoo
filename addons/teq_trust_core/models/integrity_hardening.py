# Part of TEQ Trust Egypt for Quality.

import base64
import hashlib

from odoo import api, fields, models, _
from odoo.exceptions import UserError, ValidationError


class TeqCalibrationEquipmentIntegrity(models.Model):
    _inherit = "teq.calibration.equipment"

    @api.constrains("ownership", "partner_id")
    def _check_teq_ownership_partner_integrity(self):
        for record in self:
            if record.ownership == "customer" and not record.partner_id:
                raise ValidationError(_("Customer instruments must be linked to a customer."))
            if record.ownership == "teq_standard" and record.partner_id:
                raise ValidationError(_("TEQ reference standards cannot be linked to a customer."))


class TeqCalibrationJobIntegrity(models.Model):
    _inherit = "teq.calibration.job"

    _TEQ_WORKFLOW_FIELDS = {"state", "started_at", "completed_date", "delivered_at"}
    _TEQ_IMMUTABLE_AFTER_START = {
        "partner_id",
        "contact_id",
        "equipment_id",
        "technician_id",
        "reference_standard_ids",
        "company_id",
    }

    @api.model_create_multi
    def create(self, vals_list):
        for values in vals_list:
            if values.get("state", "draft") != "draft":
                raise UserError(_("New calibration jobs must start in Draft. Use the workflow actions."))
            if set(values) & {"started_at", "completed_date", "delivered_at"}:
                raise UserError(_("Calibration workflow timestamps are controlled by the system."))
        return super().create(vals_list)

    def write(self, vals):
        changed = set(vals)
        if changed & self._TEQ_WORKFLOW_FIELDS:
            raise UserError(_("Use the calibration workflow actions to change job status or workflow timestamps."))

        for record in self:
            changed_business_fields = changed & record._BUSINESS_FIELDS
            if not changed_business_fields:
                continue
            if record.state in ("done", "delivered", "cancelled"):
                raise UserError(_("Approved, delivered, or cancelled calibration jobs are locked."))
            if record.state in ("in_progress", "review") and changed & self._TEQ_IMMUTABLE_AFTER_START:
                raise UserError(_("Customer, instrument, technician, reference standards, and company are locked after calibration starts."))

        safe_self = self.with_context(teq_calibration_workflow_transition=False)
        return super(TeqCalibrationJobIntegrity, safe_self).write(vals)

    def _teq_workflow_write(self, vals):
        """Server-only workflow transition helper.

        RPC clients cannot invoke private methods, so this avoids trusting a client-supplied
        context flag as an authorization boundary while keeping chatter/tracking behavior.
        """
        return super(
            TeqCalibrationJobIntegrity,
            self.with_context(teq_calibration_workflow_transition=True),
        ).write(vals)

    @api.constrains(
        "partner_id",
        "contact_id",
        "equipment_id",
        "reference_standard_ids",
        "company_id",
    )
    def _check_teq_job_master_data_integrity(self):
        for record in self:
            if record.equipment_id:
                if record.equipment_id.ownership != "customer":
                    raise ValidationError(_("A calibration job instrument must be a customer instrument."))
                if (
                    record.equipment_id.partner_id
                    and record.equipment_id.partner_id.commercial_partner_id
                    != record.partner_id.commercial_partner_id
                ):
                    raise ValidationError(_("The selected instrument belongs to a different customer."))

            if (
                record.contact_id
                and record.contact_id.commercial_partner_id != record.partner_id.commercial_partner_id
            ):
                raise ValidationError(_("The customer contact must belong to the selected customer."))

            invalid_standards = record.reference_standard_ids.filtered(
                lambda standard: standard.ownership != "teq_standard"
            )
            if invalid_standards:
                raise ValidationError(_("Only TEQ reference standards can be attached as calibration standards."))

    def action_mark_received(self):
        for record in self:
            if record.state != "draft":
                raise UserError(_("Only draft jobs can be marked as received."))
            if record.technician_id and record.technician_id != self.env.user and not record.can_manage_calibration:
                raise UserError(_("This job is assigned to another technician."))
            record._teq_workflow_write({"state": "received"})
        return True

    def action_start(self):
        for record in self:
            if record.state != "received":
                raise UserError(_("Receive the job before starting calibration."))
            if not record.equipment_id:
                raise UserError(_("Select the customer instrument before starting calibration."))
            if not record.technician_id:
                raise UserError(_("Assign a calibration technician before starting calibration."))
            record._check_assigned_technician_or_manager()
            record._teq_workflow_write(
                {"state": "in_progress", "started_at": fields.Datetime.now()}
            )
        return True

    def action_send_to_review(self):
        for record in self:
            if record.state != "in_progress":
                raise UserError(_("Only jobs in progress can be sent to quality review."))
            record._check_assigned_technician_or_manager()
            if not record.result_line_ids:
                raise UserError(_("Add calibration result lines before sending the job to review."))
            if record.conformity == "not_evaluated":
                raise UserError(_("All calibration result lines must be evaluated before quality review."))
            record._check_reference_standards_valid()
            record._teq_workflow_write({"state": "review"})
        return True

    def action_mark_done(self):
        self._check_quality_manager()
        today = fields.Date.context_today(self)
        for record in self:
            if record.state != "review":
                raise UserError(_("Only jobs in quality review can be approved."))
            if not record.result_line_ids:
                raise UserError(_("Calibration results are required before approval."))
            if record.conformity == "not_evaluated":
                raise UserError(_("All calibration results must be evaluated before approval."))
            record._check_reference_standards_valid()
            record._teq_workflow_write({"state": "done", "completed_date": today})
            if record.equipment_id:
                record.equipment_id.write({"last_calibration_date": today})
        return True

    def action_deliver(self):
        for record in self:
            if record.state != "done":
                raise UserError(_("Only approved calibration jobs can be delivered."))
            record._check_assigned_technician_or_manager()
            if not record.certificate_ids.filtered(lambda certificate: certificate.state == "approved"):
                raise UserError(_("Approve a calibration certificate before marking the job delivered."))
            record._teq_workflow_write(
                {"state": "delivered", "delivered_at": fields.Datetime.now()}
            )
        return True

    def action_cancel(self):
        self._check_quality_manager()
        for record in self:
            if record.state == "delivered":
                raise UserError(_("A delivered calibration job cannot be cancelled."))
            record._teq_workflow_write({"state": "cancelled"})
        return True

    def action_reset_to_draft(self):
        self._check_quality_manager()
        for record in self:
            if record.state != "cancelled":
                raise UserError(_("Only cancelled jobs can be reset to draft."))
            record._teq_workflow_write(
                {
                    "state": "draft",
                    "started_at": False,
                    "completed_date": False,
                    "delivered_at": False,
                }
            )
        return True


class TeqCalibrationResultLineIntegrity(models.Model):
    _inherit = "teq.calibration.result.line"

    def _teq_check_result_editable(self):
        is_manager = self.env.user.has_group("teq_trust_core.group_teq_calibration_manager")
        for line in self:
            job = line.job_id
            if job.certificate_ids.filtered(lambda certificate: certificate.state == "approved"):
                raise UserError(_("Void the approved certificate before changing calibration results."))
            if job.state not in ("in_progress", "review"):
                raise UserError(_("Calibration results are locked outside In Progress or Quality Review."))
            if not is_manager:
                if job.state != "in_progress" or job.technician_id != self.env.user:
                    raise UserError(_("Technicians can edit only their own in-progress calibration results."))

    @api.model_create_multi
    def create(self, vals_list):
        jobs = self.env["teq.calibration.job"].browse(
            [values.get("job_id") for values in vals_list if values.get("job_id")]
        )
        is_manager = self.env.user.has_group("teq_trust_core.group_teq_calibration_manager")
        for job in jobs:
            if job.certificate_ids.filtered(lambda certificate: certificate.state == "approved"):
                raise UserError(_("Void the approved certificate before adding calibration results."))
            if job.state not in ("in_progress", "review"):
                raise UserError(_("Calibration results can be added only during In Progress or Quality Review."))
            if not is_manager and (job.state != "in_progress" or job.technician_id != self.env.user):
                raise UserError(_("Technicians can add results only to their own in-progress calibration jobs."))
        return super().create(vals_list)

    def write(self, vals):
        if "job_id" in vals:
            raise UserError(_("A calibration result cannot be moved to another calibration job."))
        self._teq_check_result_editable()
        return super().write(vals)

    def unlink(self):
        self._teq_check_result_editable()
        return super().unlink()


class TeqCalibrationCertificateIntegrity(models.Model):
    _inherit = "teq.calibration.certificate"

    _TEQ_SYSTEM_FIELDS = {"name", "state", "approved_by", "approved_at"}

    @api.model_create_multi
    def create(self, vals_list):
        for values in vals_list:
            if values.get("state", "draft") != "draft":
                raise UserError(_("New certificates must start in Draft and be approved through the workflow."))
            if set(values) & {"approved_by", "approved_at"}:
                raise UserError(_("Certificate approval metadata is controlled by the system."))
        return super().create(vals_list)

    def write(self, vals):
        if set(vals) & self._TEQ_SYSTEM_FIELDS:
            raise UserError(_("Certificate number, status, and approval metadata are controlled by the workflow."))
        for record in self:
            if record.state == "void" and "void_reason" in vals:
                raise UserError(_("A voided certificate's void reason is immutable."))
        safe_self = self.with_context(teq_certificate_workflow_transition=False)
        return super(TeqCalibrationCertificateIntegrity, safe_self).write(vals)

    def _teq_workflow_write(self, vals):
        return super(
            TeqCalibrationCertificateIntegrity,
            self.with_context(teq_certificate_workflow_transition=True),
        ).write(vals)

    def action_approve(self):
        self._check_certificate_manager()
        for record in self:
            if record.state != "draft":
                raise UserError(_("Only draft certificates can be approved."))
            if record.job_id.state not in ("done", "delivered"):
                raise UserError(_("The calibration job must be approved before its certificate."))
            if record.job_id.conformity == "not_evaluated":
                raise UserError(_("The calibration job results have not been fully evaluated."))
            if record.result != record.job_id.conformity:
                raise UserError(_("Certificate result must match the approved calibration job conformity."))
            other_approved = self.search_count(
                [
                    ("job_id", "=", record.job_id.id),
                    ("state", "=", "approved"),
                    ("id", "!=", record.id),
                ]
            )
            if other_approved:
                raise UserError(_("Void the existing approved certificate before approving a replacement."))
            record._teq_workflow_write(
                {
                    "state": "approved",
                    "approved_by": self.env.user.id,
                    "approved_at": fields.Datetime.now(),
                }
            )
            if record.equipment_id:
                record.equipment_id.write({"last_calibration_date": record.calibration_date})
        return True

    def action_void(self):
        self._check_certificate_manager()
        for record in self:
            if record.state != "approved":
                raise UserError(_("Only approved certificates can be voided."))
            if not (record.void_reason or "").strip():
                raise UserError(_("Enter a void reason before voiding the certificate."))
            record._teq_workflow_write({"state": "void"})
        return True


class TeqSignRequestIntegrity(models.Model):
    _inherit = "teq.sign.request"

    document_sha256 = fields.Char(
        string="Document SHA-256",
        readonly=True,
        copy=False,
        help="Fingerprint captured when the document is sent, used to detect document changes before sign-off.",
    )
    _TEQ_SYSTEM_FIELDS = {"name", "state", "signed_at", "document_sha256"}

    @api.model_create_multi
    def create(self, vals_list):
        for values in vals_list:
            if values.get("state", "draft") != "draft":
                raise UserError(_("New sign-off requests must start in Draft."))
            if set(values) & {"signed_at", "document_sha256"}:
                raise UserError(_("Sign-off audit metadata is controlled by the system."))
        return super().create(vals_list)

    def write(self, vals):
        if set(vals) & self._TEQ_SYSTEM_FIELDS:
            raise UserError(_("Request number, status, signature timestamp, and document hash are controlled by the workflow."))

        for record in self:
            if record.state == "sent" and set(vals) & record._SIGNER_SENT_FIELDS:
                if record.signer_id != self.env.user:
                    raise UserError(_("Only the assigned signer can add a signature image or refusal reason."))

        safe_self = self.with_context(teq_sign_workflow_transition=False)
        return super(TeqSignRequestIntegrity, safe_self).write(vals)

    def _teq_workflow_write(self, vals):
        return super(
            TeqSignRequestIntegrity,
            self.with_context(teq_sign_workflow_transition=True),
        ).write(vals)

    def _check_signer_or_manager(self):
        for record in self:
            if record.signer_id != self.env.user:
                raise UserError(_("Only the assigned signer can sign or refuse this request."))

    def _teq_document_hash(self):
        self.ensure_one()
        if not self.document:
            return False
        payload = base64.b64decode(self.document)
        return hashlib.sha256(payload).hexdigest()

    def action_send(self):
        self._check_requester_or_manager()
        for record in self:
            if record.state != "draft":
                raise UserError(_("Only draft requests can be sent for signature."))
            if not record.document:
                raise UserError(_("Upload the document before sending it for signature."))
            if not record.signer_id:
                raise UserError(_("Choose a signer before sending the request."))
            record._teq_workflow_write(
                {"state": "sent", "document_sha256": record._teq_document_hash()}
            )
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
            if not record.document_sha256 or record.document_sha256 != record._teq_document_hash():
                raise UserError(_("The document changed after it was sent. Reset the request and send it again."))
            record._teq_workflow_write(
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
            record._teq_workflow_write({"state": "refused"})
            record._close_signature_activities(_("Signature request refused."))
        return True

    def action_cancel(self):
        self._check_requester_or_manager()
        for record in self:
            if record.state in ("signed", "cancelled"):
                raise UserError(_("Signed or already-cancelled requests cannot be cancelled."))
            record._teq_workflow_write({"state": "cancelled"})
            record._close_signature_activities(_("Signature request cancelled."))
        return True

    def action_reset_to_draft(self):
        self._check_sign_manager()
        for record in self:
            if record.state not in ("refused", "cancelled"):
                raise UserError(_("Only refused or cancelled requests can be reset to draft."))
            record._close_signature_activities(_("Signature request reset by a manager."))
            record._teq_workflow_write(
                {
                    "state": "draft",
                    "signature_image": False,
                    "signed_at": False,
                    "refusal_reason": False,
                    "document_sha256": False,
                }
            )
        return True


class TeqHrAppraisalIntegrity(models.Model):
    _inherit = "teq.hr.appraisal"

    @api.model_create_multi
    def create(self, vals_list):
        for values in vals_list:
            if values.get("state", "draft") != "draft":
                raise UserError(_("New appraisals must start in Draft and use the appraisal workflow."))
        return super().create(vals_list)

    def write(self, vals):
        if "state" in vals:
            raise UserError(_("Use the appraisal workflow actions to change appraisal status."))
        for record in self:
            if record.state in ("done", "cancelled") and set(vals) & record._APPRAISAL_FIELDS:
                raise UserError(_("Completed or cancelled appraisals are locked."))
        safe_self = self.with_context(teq_appraisal_workflow_transition=False)
        return super(TeqHrAppraisalIntegrity, safe_self).write(vals)

    def _teq_workflow_write(self, vals):
        return super(
            TeqHrAppraisalIntegrity,
            self.with_context(teq_appraisal_workflow_transition=True),
        ).write(vals)

    def action_employee_input(self):
        self._check_appraisal_manager()
        for record in self:
            if record.state != "draft":
                raise UserError(_("Only draft appraisals can request employee input."))
            if not record.employee_id.user_id:
                raise UserError(_("Link the employee to an Odoo user before requesting employee input."))
            record._teq_workflow_write({"state": "employee"})
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
            record._teq_workflow_write({"state": "manager"})
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
            record._teq_workflow_write({"state": "done"})
        return True

    def action_cancel(self):
        self._check_appraisal_manager()
        for record in self:
            if record.state in ("done", "cancelled"):
                raise UserError(_("Completed or already-cancelled appraisals cannot be cancelled."))
            record._close_employee_input_activity(_("Appraisal cancelled by a manager."))
            record._teq_workflow_write({"state": "cancelled"})
        return True

    def action_reset_to_draft(self):
        self._check_appraisal_manager()
        for record in self:
            if record.state != "cancelled":
                raise UserError(_("Only cancelled appraisals can be reset to draft."))
            record._teq_workflow_write({"state": "draft"})
        return True


class TeqEsgMetricIntegrity(models.Model):
    _inherit = "teq.esg.metric"

    @api.constrains("responsible_id", "company_id")
    def _check_teq_responsible_company(self):
        for record in self:
            if record.responsible_id and record.company_id not in record.responsible_id.company_ids:
                raise ValidationError(_("The ESG responsible user must have access to the metric company."))
