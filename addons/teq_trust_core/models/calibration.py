# Part of TEQ Trust Egypt for Quality.

from dateutil.relativedelta import relativedelta

from odoo import api, fields, models, _
from odoo.exceptions import UserError, ValidationError


class TeqCalibrationEquipment(models.Model):
    _name = "teq.calibration.equipment"
    _description = "Calibration Equipment / Instrument"
    _inherit = ["mail.thread", "mail.activity.mixin"]
    _order = "next_due_date, name"

    name = fields.Char(required=True, tracking=True)
    equipment_code = fields.Char(string="Equipment ID / Asset No.", tracking=True, index=True)
    serial_number = fields.Char(tracking=True, index=True)
    manufacturer = fields.Char()
    model = fields.Char()
    range_text = fields.Char(string="Range")
    resolution = fields.Char()
    unit = fields.Char()
    location = fields.Char()
    ownership = fields.Selection([("customer", "Customer Instrument"), ("teq_standard", "TEQ Reference Standard")], default="customer", required=True, tracking=True)
    partner_id = fields.Many2one("res.partner", string="Customer", tracking=True, domain=[("is_company", "=", True)])
    assigned_user_id = fields.Many2one("res.users", string="Responsible User", default=lambda self: self.env.user, domain=[("share", "=", False)], tracking=True)
    calibration_interval_months = fields.Integer(string="Calibration Interval (Months)", default=12, required=True, tracking=True)
    last_calibration_date = fields.Date(tracking=True)
    next_due_date = fields.Date(compute="_compute_next_due_date", store=True, tracking=True)
    due_status = fields.Selection([("not_calibrated", "Not Calibrated"), ("valid", "Valid"), ("due_soon", "Due Soon"), ("overdue", "Overdue")], compute="_compute_due_status")
    reference_certificate_no = fields.Char(string="Reference Certificate No.")
    traceability_lab = fields.Char(string="Traceability / Calibration Lab")
    notes = fields.Html()
    active = fields.Boolean(default=True)
    reminder_sent = fields.Boolean(default=False, copy=False)
    company_id = fields.Many2one("res.company", required=True, default=lambda self: self.env.company)
    job_ids = fields.One2many("teq.calibration.job", "equipment_id", string="Calibration Jobs")
    job_count = fields.Integer(compute="_compute_job_count")

    _sql_constraints = [("positive_calibration_interval", "CHECK(calibration_interval_months > 0)", "Calibration interval must be greater than zero.")]

    @api.depends("last_calibration_date", "calibration_interval_months")
    def _compute_next_due_date(self):
        for record in self:
            record.next_due_date = record.last_calibration_date + relativedelta(months=record.calibration_interval_months) if record.last_calibration_date and record.calibration_interval_months else False

    @api.depends("next_due_date")
    def _compute_due_status(self):
        today = fields.Date.context_today(self)
        soon = today + relativedelta(days=30)
        for record in self:
            if not record.next_due_date:
                record.due_status = "not_calibrated"
            elif record.next_due_date < today:
                record.due_status = "overdue"
            elif record.next_due_date <= soon:
                record.due_status = "due_soon"
            else:
                record.due_status = "valid"

    @api.depends("job_ids")
    def _compute_job_count(self):
        for record in self:
            record.job_count = len(record.job_ids)

    def write(self, vals):
        if "last_calibration_date" in vals or "calibration_interval_months" in vals:
            vals["reminder_sent"] = False
        return super().write(vals)

    def action_view_jobs(self):
        self.ensure_one()
        return {"type": "ir.actions.act_window", "name": _("Calibration Jobs"), "res_model": "teq.calibration.job", "view_mode": "list,form", "domain": [("equipment_id", "=", self.id)], "context": {"default_equipment_id": self.id, "default_partner_id": self.partner_id.id}}

    @api.model
    def _cron_schedule_due_activities(self):
        today = fields.Date.context_today(self)
        threshold = today + relativedelta(days=30)
        equipments = self.search([("active", "=", True), ("next_due_date", "!=", False), ("next_due_date", "<=", threshold), ("reminder_sent", "=", False)])
        for equipment in equipments:
            user = equipment.assigned_user_id or equipment.create_uid
            if not user:
                continue
            equipment.activity_schedule("mail.mail_activity_data_todo", user_id=user.id, date_deadline=equipment.next_due_date, summary=_("Calibration due: %s") % equipment.display_name, note=_("This instrument is due for calibration on %s.") % equipment.next_due_date)
            equipment.reminder_sent = True
        return True


class TeqCalibrationJob(models.Model):
    _name = "teq.calibration.job"
    _description = "Calibration Job"
    _inherit = ["mail.thread", "mail.activity.mixin"]
    _order = "id desc"

    name = fields.Char(default=lambda self: _("New"), copy=False, readonly=True, index=True)
    partner_id = fields.Many2one("res.partner", string="Customer", required=True, tracking=True, domain=[("is_company", "=", True)])
    contact_id = fields.Many2one("res.partner", string="Customer Contact", tracking=True)
    equipment_id = fields.Many2one("teq.calibration.equipment", string="Instrument", tracking=True, domain="[('ownership', '=', 'customer'), '|', ('partner_id', '=', partner_id), ('partner_id', '=', False)]")
    technician_id = fields.Many2one("res.users", string="Calibration Technician", tracking=True, domain=[("share", "=", False)])
    reference_standard_ids = fields.Many2many("teq.calibration.equipment", "teq_calibration_job_standard_rel", "job_id", "equipment_id", string="Reference Standards Used", domain=[("ownership", "=", "teq_standard")])
    received_date = fields.Date(default=fields.Date.context_today, tracking=True)
    scheduled_date = fields.Datetime(tracking=True)
    started_at = fields.Datetime(readonly=True, tracking=True)
    completed_date = fields.Date(readonly=True, tracking=True)
    delivered_at = fields.Datetime(readonly=True, tracking=True)
    state = fields.Selection([("draft", "Draft"), ("received", "Received"), ("in_progress", "In Progress"), ("review", "Quality Review"), ("done", "Calibrated"), ("delivered", "Delivered"), ("cancelled", "Cancelled")], default="draft", required=True, tracking=True)
    service_product_id = fields.Many2one("product.product", string="Calibration Service Product", domain=[("type", "=", "service")])
    quoted_price = fields.Monetary()
    currency_id = fields.Many2one(related="company_id.currency_id", store=True, readonly=True)
    sale_order_id = fields.Many2one("sale.order", string="Quotation / Sales Order", copy=False)
    invoice_id = fields.Many2one("account.move", compute="_compute_invoice_id", string="Invoice")
    result_line_ids = fields.One2many("teq.calibration.result.line", "job_id", string="Calibration Results", copy=True)
    conformity = fields.Selection([("not_evaluated", "Not Evaluated"), ("pass", "Pass"), ("fail", "Fail")], compute="_compute_conformity", store=True)
    certificate_ids = fields.One2many("teq.calibration.certificate", "job_id", string="Certificates")
    certificate_count = fields.Integer(compute="_compute_certificate_count")
    customer_po = fields.Char(string="Customer PO / Reference")
    method = fields.Char(string="Calibration Method")
    environmental_conditions = fields.Char(string="Environmental Conditions")
    notes = fields.Html()
    company_id = fields.Many2one("res.company", required=True, default=lambda self: self.env.company)

    @api.model_create_multi
    def create(self, vals_list):
        sequence = self.env["ir.sequence"]
        for vals in vals_list:
            if vals.get("name", _("New")) == _("New"):
                vals["name"] = sequence.next_by_code("teq.calibration.job") or _("New")
        return super().create(vals_list)

    @api.onchange("equipment_id")
    def _onchange_equipment_id(self):
        if self.equipment_id and self.equipment_id.partner_id:
            self.partner_id = self.equipment_id.partner_id

    @api.onchange("service_product_id")
    def _onchange_service_product_id(self):
        if self.service_product_id and not self.quoted_price:
            self.quoted_price = self.service_product_id.lst_price

    @api.depends("sale_order_id", "sale_order_id.invoice_ids")
    def _compute_invoice_id(self):
        for record in self:
            invoices = record.sale_order_id.invoice_ids.filtered(lambda move: move.move_type in ("out_invoice", "out_refund"))
            record.invoice_id = invoices[:1].id if invoices else False

    @api.depends("result_line_ids.outcome")
    def _compute_conformity(self):
        for record in self:
            outcomes = record.result_line_ids.mapped("outcome")
            if "fail" in outcomes:
                record.conformity = "fail"
            elif outcomes and all(outcome == "pass" for outcome in outcomes):
                record.conformity = "pass"
            else:
                record.conformity = "not_evaluated"

    @api.depends("certificate_ids")
    def _compute_certificate_count(self):
        for record in self:
            record.certificate_count = len(record.certificate_ids)

    def action_mark_received(self):
        self.write({"state": "received"}); return True

    def action_start(self):
        for record in self:
            if not record.equipment_id:
                raise UserError(_("Select the customer instrument before starting calibration."))
            if not record.technician_id:
                raise UserError(_("Assign a calibration technician before starting calibration."))
            record.write({"state": "in_progress", "started_at": fields.Datetime.now()})
        return True

    def action_send_to_review(self):
        for record in self:
            if not record.result_line_ids:
                raise UserError(_("Add calibration result lines before sending the job to review."))
            record.state = "review"
        return True

    def action_mark_done(self):
        today = fields.Date.context_today(self)
        for record in self:
            if record.state not in ("review", "in_progress"):
                raise UserError(_("Only jobs in progress or quality review can be completed."))
            record.write({"state": "done", "completed_date": today})
            if record.equipment_id:
                record.equipment_id.write({"last_calibration_date": today})
        return True

    def action_deliver(self):
        for record in self:
            if record.state != "done":
                raise UserError(_("Only calibrated jobs can be delivered."))
            record.write({"state": "delivered", "delivered_at": fields.Datetime.now()})
        return True

    def action_cancel(self): self.write({"state": "cancelled"}); return True
    def action_reset_to_draft(self): self.write({"state": "draft", "started_at": False, "completed_date": False, "delivered_at": False}); return True

    def action_create_quotation(self):
        self.ensure_one()
        if self.sale_order_id:
            return self.action_open_quotation()
        if not self.service_product_id:
            raise UserError(_("Select a calibration service product first."))
        order = self.env["sale.order"].create({"partner_id": self.partner_id.id, "origin": self.name, "client_order_ref": self.customer_po})
        line_name = _("Calibration service")
        if self.equipment_id:
            line_name = _("Calibration: %(equipment)s (S/N: %(serial)s)", equipment=self.equipment_id.display_name, serial=self.equipment_id.serial_number or "-")
        self.env["sale.order.line"].create({"order_id": order.id, "product_id": self.service_product_id.id, "product_uom_qty": 1.0, "price_unit": self.quoted_price or self.service_product_id.lst_price, "name": line_name})
        self.sale_order_id = order
        return self.action_open_quotation()

    def action_open_quotation(self):
        self.ensure_one()
        if not self.sale_order_id: raise UserError(_("No quotation is linked to this calibration job."))
        return {"type": "ir.actions.act_window", "name": _("Quotation / Sales Order"), "res_model": "sale.order", "view_mode": "form", "res_id": self.sale_order_id.id}

    def action_open_invoice(self):
        self.ensure_one()
        if not self.invoice_id: raise UserError(_("No customer invoice is linked yet."))
        return {"type": "ir.actions.act_window", "name": _("Invoice"), "res_model": "account.move", "view_mode": "form", "res_id": self.invoice_id.id}

    def action_create_certificate(self):
        self.ensure_one()
        if self.state not in ("review", "done", "delivered"):
            raise UserError(_("The job must be in quality review or completed before creating a certificate."))
        certificate = self.env["teq.calibration.certificate"].create({"job_id": self.id, "calibration_date": self.completed_date or fields.Date.context_today(self), "result": self.conformity})
        return {"type": "ir.actions.act_window", "name": _("Calibration Certificate"), "res_model": "teq.calibration.certificate", "view_mode": "form", "res_id": certificate.id}

    def action_view_certificates(self):
        self.ensure_one()
        return {"type": "ir.actions.act_window", "name": _("Calibration Certificates"), "res_model": "teq.calibration.certificate", "view_mode": "list,form", "domain": [("job_id", "=", self.id)], "context": {"default_job_id": self.id}}


class TeqCalibrationResultLine(models.Model):
    _name = "teq.calibration.result.line"
    _description = "Calibration Result Line"
    _order = "sequence, id"

    sequence = fields.Integer(default=10)
    job_id = fields.Many2one("teq.calibration.job", required=True, ondelete="cascade")
    test_point = fields.Char(required=True)
    nominal_value = fields.Float()
    measured_value = fields.Float()
    deviation = fields.Float(compute="_compute_deviation", store=True)
    uncertainty = fields.Float()
    tolerance_min = fields.Float()
    tolerance_max = fields.Float()
    unit = fields.Char()
    outcome = fields.Selection([("not_evaluated", "Not Evaluated"), ("pass", "Pass"), ("fail", "Fail")], compute="_compute_outcome", store=True)
    notes = fields.Char()

    @api.depends("nominal_value", "measured_value")
    def _compute_deviation(self):
        for line in self: line.deviation = line.measured_value - line.nominal_value

    @api.depends("measured_value", "tolerance_min", "tolerance_max")
    def _compute_outcome(self):
        for line in self:
            if line.tolerance_min == 0 and line.tolerance_max == 0: line.outcome = "not_evaluated"
            elif line.tolerance_min <= line.measured_value <= line.tolerance_max: line.outcome = "pass"
            else: line.outcome = "fail"

    @api.constrains("tolerance_min", "tolerance_max")
    def _check_tolerance(self):
        for line in self:
            if line.tolerance_min and line.tolerance_max and line.tolerance_min > line.tolerance_max:
                raise ValidationError(_("Minimum tolerance cannot be greater than maximum tolerance."))


class TeqCalibrationCertificate(models.Model):
    _name = "teq.calibration.certificate"
    _description = "Calibration Certificate"
    _inherit = ["mail.thread", "mail.activity.mixin"]
    _order = "id desc"

    name = fields.Char(string="Certificate No.", default=lambda self: _("New"), copy=False, readonly=True, index=True)
    job_id = fields.Many2one("teq.calibration.job", required=True, ondelete="restrict", tracking=True)
    partner_id = fields.Many2one(related="job_id.partner_id", store=True)
    equipment_id = fields.Many2one(related="job_id.equipment_id", store=True)
    calibration_date = fields.Date(required=True, tracking=True)
    valid_until = fields.Date(compute="_compute_valid_until", store=True)
    result = fields.Selection([("not_evaluated", "Not Evaluated"), ("pass", "Pass"), ("fail", "Fail")], default="not_evaluated", required=True, tracking=True)
    state = fields.Selection([("draft", "Draft"), ("approved", "Approved"), ("void", "Void")], default="draft", required=True, tracking=True)
    approved_by = fields.Many2one("res.users", readonly=True)
    approved_at = fields.Datetime(readonly=True)
    statement = fields.Html(default="<p>Results are valid only for the instrument identified on this certificate.</p>")
    company_id = fields.Many2one(related="job_id.company_id", store=True, readonly=True)

    @api.model_create_multi
    def create(self, vals_list):
        sequence = self.env["ir.sequence"]
        for vals in vals_list:
            if vals.get("name", _("New")) == _("New"):
                vals["name"] = sequence.next_by_code("teq.calibration.certificate") or _("New")
        return super().create(vals_list)

    @api.depends("calibration_date", "equipment_id.calibration_interval_months")
    def _compute_valid_until(self):
        for record in self:
            interval = record.equipment_id.calibration_interval_months or 0
            record.valid_until = record.calibration_date + relativedelta(months=interval) if record.calibration_date and interval else False

    def action_approve(self):
        for record in self:
            if record.result == "not_evaluated": raise UserError(_("Set the certificate result before approval."))
            record.write({"state": "approved", "approved_by": self.env.user.id, "approved_at": fields.Datetime.now()})
            if record.equipment_id: record.equipment_id.write({"last_calibration_date": record.calibration_date})
        return True

    def action_void(self): self.write({"state": "void"}); return True
    def action_reset_to_draft(self): self.write({"state": "draft", "approved_by": False, "approved_at": False}); return True


class ResPartner(models.Model):
    _inherit = "res.partner"

    teq_equipment_ids = fields.One2many("teq.calibration.equipment", "partner_id", string="Calibration Instruments")
    teq_equipment_count = fields.Integer(compute="_compute_teq_calibration_counts")
    teq_calibration_job_count = fields.Integer(compute="_compute_teq_calibration_counts")

    def _compute_teq_calibration_counts(self):
        Equipment, Job = self.env["teq.calibration.equipment"], self.env["teq.calibration.job"]
        for partner in self:
            partner.teq_equipment_count = Equipment.search_count([("partner_id", "=", partner.id)])
            partner.teq_calibration_job_count = Job.search_count([("partner_id", "=", partner.id)])

    def action_teq_view_equipment(self):
        self.ensure_one(); return {"type": "ir.actions.act_window", "name": _("Calibration Instruments"), "res_model": "teq.calibration.equipment", "view_mode": "list,form", "domain": [("partner_id", "=", self.id)], "context": {"default_partner_id": self.id, "default_ownership": "customer"}}

    def action_teq_view_calibration_jobs(self):
        self.ensure_one(); return {"type": "ir.actions.act_window", "name": _("Calibration Jobs"), "res_model": "teq.calibration.job", "view_mode": "list,form", "domain": [("partner_id", "=", self.id)], "context": {"default_partner_id": self.id}}


class SaleOrder(models.Model):
    _inherit = "sale.order"

    teq_calibration_job_ids = fields.One2many("teq.calibration.job", "sale_order_id", string="Calibration Jobs")
    teq_calibration_job_count = fields.Integer(compute="_compute_teq_calibration_job_count")

    def _compute_teq_calibration_job_count(self):
        for order in self: order.teq_calibration_job_count = len(order.teq_calibration_job_ids)

    def action_teq_create_calibration_job(self):
        self.ensure_one()
        first_service_line = self.order_line.filtered(lambda line: line.product_id and line.product_id.type == "service")[:1]
        job = self.env["teq.calibration.job"].create({"partner_id": self.partner_id.commercial_partner_id.id, "contact_id": self.partner_id.id, "sale_order_id": self.id, "service_product_id": first_service_line.product_id.id if first_service_line else False, "quoted_price": first_service_line.price_unit if first_service_line else 0.0, "customer_po": self.client_order_ref})
        return {"type": "ir.actions.act_window", "name": _("Calibration Job"), "res_model": "teq.calibration.job", "view_mode": "form", "res_id": job.id}

    def action_teq_view_calibration_jobs(self):
        self.ensure_one(); return {"type": "ir.actions.act_window", "name": _("Calibration Jobs"), "res_model": "teq.calibration.job", "view_mode": "list,form", "domain": [("sale_order_id", "=", self.id)], "context": {"default_partner_id": self.partner_id.commercial_partner_id.id, "default_sale_order_id": self.id}}
