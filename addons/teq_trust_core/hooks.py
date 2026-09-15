# Part of TEQ Trust Egypt for Quality.


def _existing_groups(env, xmlids):
    groups = env["res.groups"]
    for xmlid in xmlids:
        group = env.ref(xmlid, raise_if_not_found=False)
        if group and group._name == "res.groups":
            groups |= group
    return groups


def post_init_hook(env):
    main_company = env.ref("base.main_company", raise_if_not_found=False)
    if main_company:
        main_company.write({"name": "TEQ Trust Egypt for Quality"})

    helper = env["teq.access.profile.mixin"]
    highest_groups = helper._teq_select_highest_groups()
    master_group = env.ref("teq_trust_core.group_teq_master_admin")
    system_group = env.ref("base.group_system")

    admin_users = env["res.users"].browse([
        user.id
        for user in (
            env.ref("base.user_root", raise_if_not_found=False),
            env.ref("base.user_admin", raise_if_not_found=False),
        )
        if user
    ])
    full_groups = highest_groups | master_group | system_group
    for user in admin_users:
        user.sudo().write({"group_ids": [(4, group.id) for group in full_groups]})

    profiles = {
        "TEQ Master Administrator": [],
        "General Internal User": ["base.group_user"],
        "Calibration Technician": ["teq_trust_core.group_teq_calibration_user"],
        "Calibration & Quality Manager": ["teq_trust_core.group_teq_calibration_manager"],
        "Sales User - Own Documents": ["sales_team.group_sale_salesman"],
        "Sales User - All Documents": ["sales_team.group_sale_salesman_all_leads"],
        "Sales & CRM Manager": ["sales_team.group_sale_manager"],
        "Invoicing / Billing User": ["account.group_account_invoice"],
        "Finance Manager": ["account.group_account_manager"],
        "Inventory User": ["stock.group_stock_user"],
        "Purchase User": ["purchase.group_purchase_user"],
        "Inventory & Purchase Manager": ["stock.group_stock_manager", "purchase.group_purchase_manager"],
        "HR Officer": ["hr.group_hr_user"],
        "Human Resources Manager": [
            "hr.group_hr_manager", "hr_holidays.group_hr_holidays_manager",
            "hr_expense.group_hr_expense_manager", "teq_trust_core.group_teq_appraisal_manager"
        ],
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

    Profile = env["teq.access.profile"].sudo()
    for name, xmlids in profiles.items():
        groups = full_groups if name == "TEQ Master Administrator" else _existing_groups(env, xmlids)
        profile = Profile.search([("name", "=", name)], limit=1)
        values = {
            "name": name,
            "description": "Preconfigured TEQ role profile. Combine profiles on a user when required.",
            "group_ids": [(6, 0, groups.ids)],
        }
        if profile:
            profile.write(values)
        else:
            Profile.create(values)
