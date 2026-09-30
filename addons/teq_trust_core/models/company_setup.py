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

        if company.name == "My Company":
            company.sudo().write({"name": "TEQ Trust Egypt for Quality"})

        # Set the fiscal country before loading the chart. Odoo can install/reload
        # localization data when the country changes, so re-browse afterwards.
        if egypt and not company.country_id:
            company.sudo().write({"country_id": egypt.id})
            company = self.browse(company.id)

        if (
            egypt
            and company.country_id == egypt
            and not company._existing_accounting()
            and company.chart_template != "eg"
        ):
            self.env["account.chart.template"].sudo().try_loading("eg", company)
            company = self.browse(company.id)

        # The stock database starts in USD. Set EGP only for an unused ledger;
        # never rewrite the currency of a company that already has entries.
        if (
            egp
            and usd
            and not company._existing_accounting()
            and company.currency_id == usd
        ):
            company.sudo().write({"currency_id": egp.id})

        return True
