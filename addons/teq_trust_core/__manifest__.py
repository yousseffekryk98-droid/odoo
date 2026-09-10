{
    "name": "TEQ Trust Egypt ERP",
    "version": "19.0.1.0.0",
    "summary": "Complete ERP and calibration management for TEQ Trust Egypt for Quality",
    "category": "Administration",
    "author": "TEQ Trust Egypt for Quality",
    "license": "LGPL-3",
    "depends": [
        "mail", "sale_management", "crm", "point_of_sale", "account", "hr_expense", "spreadsheet",
        "stock", "purchase", "purchase_stock", "sale_stock", "maintenance", "hr", "hr_holidays",
        "fleet", "survey", "project", "sale_project"
    ],
    "data": [
        "security/teq_security.xml",
        "security/ir.model.access.csv",
        "data/teq_data.xml",
        "report/calibration_certificate_report.xml",
        "views/access_profile_views.xml",
        "views/res_users_views.xml",
        "views/calibration_views.xml",
        "views/sign_request_views.xml",
        "views/appraisal_views.xml",
        "views/esg_views.xml"
    ],
    "post_init_hook": "post_init_hook",
    "application": true,
    "installable": true
}
