# Part of TEQ Trust Egypt for Quality.

from odoo import api, fields, models, _
from odoo.exceptions import UserError, ValidationError


class TeqEmployeeOnboarding(models.TransientModel):
    _name = "teq.employee.onboarding"
    _description = "TEQ Employee and User Onboarding"

    name = fields.Char(string="Employee Name", required=True)
    create_login = fields.Boolean(
        string="Create Odoo Login",
        default=True,
        help="Create an internal Odoo user and link it to the employee.",
    )
    login = fields.Char(string="Login / Work Email")
    email = fields.Char(string="Work Email")
    phone = fields.Char(string="Work Phone")
    initial_password = fields.Char(string="Initial Password")
    confirm_password = fields.Char(string="Confirm Password")
    job_title = fields.Char(string="Job Title")
    department_id = fields.Many2one(
        "hr.department",
        string="Department",
        domain="['|', ('company_id', '=', False), ('company_id', '=', company_id)]",
    )
    manager_id = fields.Many2one(
        "hr.employee",
        string="Manager",
        domain="[('company_id', '=', company_id)]",
    )
    company_id = fields.Many2one(
        "res.company",
        string="Company",
        required=True,
        default=lambda self: self.env.company,
    )
    access_profile_ids = fields.Many2many(
        "teq.access.profile",
        string="TEQ Roles / Access Profiles",
        domain=[("active", "=", True)],
        help="Role bundles are applied immediately to the new user.",
    )

    @api.onchange("email")
    def _onchange_email(self):
        if self.email and not self.login:
            self.login = self.email

    @api.onchange("company_id")
    def _onchange_company_id(self):
        if (
            self.department_id
            and self.department_id.company_id
            and self.department_id.company_id != self.company_id
        ):
            self.department_id = False
        if self.manager_id and self.manager_id.company_id != self.company_id:
            self.manager_id = False

    @api.constrains("create_login", "login", "initial_password", "confirm_password")
    def _check_login_credentials(self):
        for wizard in self:
            if not wizard.create_login:
                continue
            if not (wizard.login or "").strip():
                raise ValidationError(_("Login / Work Email is required when creating an Odoo login."))
            if len(wizard.initial_password or "") < 8:
                raise ValidationError(_("The initial password must contain at least 8 characters."))
            if wizard.initial_password != wizard.confirm_password:
                raise ValidationError(_("The password confirmation does not match."))

    @api.constrains("company_id", "department_id", "manager_id")
    def _check_company_relationships(self):
        for wizard in self:
            if wizard.department_id.company_id and wizard.department_id.company_id != wizard.company_id:
                raise ValidationError(_("The department must belong to the selected company."))
            if wizard.manager_id and wizard.manager_id.company_id != wizard.company_id:
                raise ValidationError(_("The manager must belong to the selected company."))

    def _check_master_admin(self):
        if not self.env.user.has_group("teq_trust_core.group_teq_master_admin"):
            raise UserError(_("Only a TEQ Master Administrator can onboard system users."))

    def action_create_employee(self):
        self.ensure_one()
        self._check_master_admin()

        User = self.env["res.users"].with_context(active_test=False)
        login = (self.login or self.email or "").strip()
        email = (self.email or login).strip()

        user = self.env["res.users"]
        if self.create_login:
            if User.search([("login", "=ilike", login)], limit=1):
                raise UserError(_("A user with login '%s' already exists.") % login)

            internal_group = self.env.ref("base.group_user")
            user = User.create(
                {
                    "name": self.name.strip(),
                    "login": login,
                    "email": email or False,
                    "phone": self.phone or False,
                    "company_id": self.company_id.id,
                    "company_ids": [(6, 0, [self.company_id.id])],
                    "group_ids": [(4, internal_group.id)],
                    "password": self.initial_password,
                    "create_employee": True,
                    "teq_access_profile_ids": [(6, 0, self.access_profile_ids.ids)],
                }
            )
            employee = user.employee_id
        else:
            employee = self.env["hr.employee"].create(
                {
                    "name": self.name.strip(),
                    "company_id": self.company_id.id,
                    "work_email": email or False,
                    "work_phone": self.phone or False,
                }
            )

        if not employee:
            raise UserError(_("The employee record could not be created."))

        employee.write(
            {
                "job_title": self.job_title or False,
                "department_id": self.department_id.id or False,
                "parent_id": self.manager_id.id or False,
                "work_email": email or False,
                "work_phone": self.phone or False,
            }
        )

        if self.create_login:
            return {
                "type": "ir.actions.act_window",
                "name": _("User Account"),
                "res_model": "res.users",
                "res_id": user.id,
                "view_mode": "form",
                "target": "current",
            }

        return {
            "type": "ir.actions.act_window",
            "name": _("Employee"),
            "res_model": "hr.employee",
            "res_id": employee.id,
            "view_mode": "form",
            "target": "current",
        }
