# Part of TEQ Trust Egypt for Quality.

from odoo import models


class IrModuleModule(models.Model):
    _inherit = "ir.module.module"

    def _register_hook(self):
        # Let Odoo/account finish any deferred default chart initialization first.
        res = super()._register_hook()
        self.env["res.company"].teq_configure_main_company()
        return res
