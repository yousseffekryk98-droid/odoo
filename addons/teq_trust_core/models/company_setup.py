# Part of TEQ Trust Egypt for Quality.

from odoo import api, models


class ResCompany(models.Model):
    _inherit = "res.company"

    @api.model
    def teq_configure_main_company(self):
        """Apply safe TEQ Egypt defaults without overwriting live accounting data."""
        company = self.env.ref("base.main_company", raise_if_not_found=False)
        if not company:
            return True

        egypt = self.env.ref("base.eg", raise_if_not_found=False)
        egp = self.env.ref("base.EGP", raise_if_not_found=False)
        usd = self.env.ref("base.USD", raise_if_not_found=False)

        values = {}
        if company.name == "My Company":
            values["name"] = "TEQ Trust Egypt for Quality"
        if egypt and not company.country_id:
            values["country_id"] = egypt.id

        has_accounting_entries = company._existing_accounting()
        if egp and usd and not has_accounting_entries and company.currency_id == usd:
            values["currency_id"] = egp.id

        if values:
            company.sudo().write(values)

        if (
            egypt
            and company.country_id == egypt
            and not company._existing_accounting()
            and company.chart_template != "eg"
        ):
            self.env["account.chart.template"].sudo().try_loading("eg", company)

        return True
