# Part of TEQ Trust Egypt for Quality.


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

    env["teq.access.profile"].teq_seed_default_profiles()
