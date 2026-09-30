from odoo.tests import tagged
from odoo.tests.common import TransactionCase


@tagged("post_install", "-at_install")
class TestTeqCompanySetup(TransactionCase):

    def test_main_company_uses_egypt_accounting_defaults(self):
        company = self.env.ref("base.main_company")
        self.assertEqual(company.name, "TEQ Trust Egypt for Quality")
        self.assertEqual(company.country_id, self.env.ref("base.eg"))
        self.assertEqual(company.currency_id, self.env.ref("base.EGP"))
        self.assertEqual(company.chart_template, "eg")
