import base64

from odoo.exceptions import UserError
from odoo.tests import tagged
from odoo.tests.common import TransactionCase


@tagged("post_install", "-at_install")
class TestTeqSecurityWorkflows(TransactionCase):

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.admin = cls.env.ref("base.user_admin")
        cls.calibration_user_group = cls.env.ref("teq_trust_core.group_teq_calibration_user")
        cls.appraisal_user_group = cls.env.ref("teq_trust_core.group_teq_appraisal_user")
        cls.appraisal_manager_group = cls.env.ref("teq_trust_core.group_teq_appraisal_manager")
        cls.sign_user_group = cls.env.ref("teq_trust_core.group_teq_sign_user")

        User = cls.env["res.users"].with_user(cls.admin)
        cls.technician = User.create({
            "name": "TEQ Workflow Technician",
            "login": "teq.workflow.technician@example.com",
            "email": "teq.workflow.technician@example.com",
            "group_ids": [(6, 0, [cls.calibration_user_group.id])],
        })
        cls.employee_user = User.create({
            "name": "TEQ Appraisal Employee",
            "login": "teq.appraisal.employee@example.com",
            "email": "teq.appraisal.employee@example.com",
            "group_ids": [(6, 0, [cls.appraisal_user_group.id])],
            "create_employee": True,
        })
        cls.appraisal_manager = User.create({
            "name": "TEQ Appraisal Manager",
            "login": "teq.appraisal.manager@example.com",
            "email": "teq.appraisal.manager@example.com",
            "group_ids": [(6, 0, [cls.appraisal_manager_group.id])],
            "create_employee": True,
        })
        cls.requester = User.create({
            "name": "TEQ Sign Requester",
            "login": "teq.sign.requester@example.com",
            "email": "teq.sign.requester@example.com",
            "group_ids": [(6, 0, [cls.sign_user_group.id])],
        })
        cls.signer = User.create({
            "name": "TEQ Signer",
            "login": "teq.signer@example.com",
            "email": "teq.signer@example.com",
            "group_ids": [(6, 0, [cls.sign_user_group.id])],
        })

    def test_technician_cannot_approve_calibration_job(self):
        partner = self.env["res.partner"].with_user(self.admin).create({
            "name": "TEQ Calibration Client",
            "is_company": True,
        })
        equipment = self.env["teq.calibration.equipment"].with_user(self.admin).create({
            "name": "Client Pressure Gauge",
            "ownership": "customer",
            "partner_id": partner.id,
            "company_id": self.env.company.id,
        })
        job = self.env["teq.calibration.job"].with_user(self.admin).create({
            "partner_id": partner.id,
            "equipment_id": equipment.id,
            "technician_id": self.technician.id,
            "company_id": self.env.company.id,
        })

        job.with_user(self.technician).action_mark_received()
        job.with_user(self.technician).action_start()
        self.env["teq.calibration.result.line"].with_user(self.technician).create({
            "job_id": job.id,
            "test_point": "100 kPa",
            "nominal_value": 100.0,
            "measured_value": 100.0,
            "tolerance_min": 99.0,
            "tolerance_max": 101.0,
            "uncertainty": 0.1,
            "unit": "kPa",
        })
        job.with_user(self.technician).action_send_to_review()

        with self.assertRaises(UserError):
            job.with_user(self.technician).action_mark_done()

    def test_technician_cannot_edit_another_technicians_results(self):
        User = self.env["res.users"].with_user(self.admin)
        other_technician = User.create({
            "name": "Other TEQ Technician",
            "login": "teq.other.technician@example.com",
            "group_ids": [(6, 0, [self.calibration_user_group.id])],
        })
        partner = self.env["res.partner"].with_user(self.admin).create({
            "name": "Another Calibration Client",
            "is_company": True,
        })
        equipment = self.env["teq.calibration.equipment"].with_user(self.admin).create({
            "name": "Client Thermometer",
            "ownership": "customer",
            "partner_id": partner.id,
            "company_id": self.env.company.id,
        })
        job = self.env["teq.calibration.job"].with_user(self.admin).create({
            "partner_id": partner.id,
            "equipment_id": equipment.id,
            "technician_id": other_technician.id,
            "company_id": self.env.company.id,
            "state": "in_progress",
        })
        line = self.env["teq.calibration.result.line"].with_user(self.admin).create({
            "job_id": job.id,
            "test_point": "20 C",
            "nominal_value": 20.0,
            "measured_value": 20.0,
            "tolerance_min": 19.5,
            "tolerance_max": 20.5,
        })

        with self.assertRaises(Exception):
            line.with_user(self.technician).write({"measured_value": 20.1})

    def test_employee_can_edit_only_own_appraisal_feedback(self):
        employee = self.employee_user.employee_id
        manager_employee = self.appraisal_manager.employee_id
        appraisal = self.env["teq.hr.appraisal"].with_user(self.appraisal_manager).create({
            "employee_id": employee.id,
            "manager_id": manager_employee.id,
            "period_from": "2026-01-01",
            "period_to": "2026-06-30",
        })
        appraisal.with_user(self.appraisal_manager).action_employee_input()

        appraisal.with_user(self.employee_user).write({"employee_feedback": "Employee self-review."})
        with self.assertRaises(UserError):
            appraisal.with_user(self.employee_user).write({"rating": "5"})
        with self.assertRaises(UserError):
            appraisal.with_user(self.employee_user).write({"manager_feedback": "Not allowed."})

    def test_signed_request_is_immutable(self):
        request = self.env["teq.sign.request"].with_user(self.requester).create({
            "subject": "Controlled procedure approval",
            "document": base64.b64encode(b"TEQ controlled document"),
            "document_filename": "procedure.pdf",
            "signer_id": self.signer.id,
            "company_id": self.env.company.id,
        })
        request.with_user(self.requester).action_send()
        request.with_user(self.signer).write({
            "signature_image": base64.b64encode(b"signature"),
        })
        request.with_user(self.signer).action_sign()

        with self.assertRaises(UserError):
            request.with_user(self.requester).write({"subject": "Changed after signing"})
        with self.assertRaises(UserError):
            request.with_user(self.requester).write({"state": "draft"})

    def test_access_profile_change_reapplies_managed_groups(self):
        profile = self.env["teq.access.profile"].with_user(self.admin).create({
            "name": "Temporary TEQ Test Profile",
            "group_ids": [(6, 0, [self.sign_user_group.id])],
        })
        user = self.env["res.users"].with_user(self.admin).create({
            "name": "TEQ Role Propagation User",
            "login": "teq.role.propagation@example.com",
            "teq_access_profile_ids": [(6, 0, [profile.id])],
        })
        self.assertIn(self.sign_user_group, user.group_ids)

        profile.with_user(self.admin).write({"group_ids": [(5, 0, 0)]})
        self.assertNotIn(self.sign_user_group, user.group_ids)
