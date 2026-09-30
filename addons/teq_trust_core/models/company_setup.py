# Part of TEQ Trust Egypt for Quality.

from odoo import api, models


class ResCompany(models.Model):
    _inherit = "res.company"

    @api.model
    def teq_configure_main_company(self):
        """Apply TEQ Egypt defaults only while the ledger is still unused."""
        company = self.env.ref("base.main_company", raise_if_not_found=False)
        if not company:
            return True

        if company.name == "My Company":
            company.sudo().write({"name": "TEQ Trust Egypt for Quality"})

        # Never change fiscal localization or currency after accounting activity exists.
        if company._existing_accounting():
            return True

        egypt = self.env.ref("base.eg", raise_if_not_found=False)
        egp = self.env.ref("base.EGP", raise_if_not_found=False)
        if not egypt or not egp:
            return True

        if not company.country_id:
            company.sudo().write({"country_id": egypt.id})
            company = self.browse(company.id)

        # Respect an explicitly configured non-Egypt company.
        if company.country_id != egypt:
            return True

        if company.chart_template != "eg":
            self.env["account.chart.template"].sudo().try_loading("eg", company)
            company = self.browse(company.id)

        # A fresh TEQ Egypt ledger must use EGP. The chart loader normally applies
        # this itself; the explicit write protects against earlier deferred defaults.
        if not company._existing_accounting() and company.currency_id != egp:
            company.sudo().write({"currency_id": egp.id})

        return True
