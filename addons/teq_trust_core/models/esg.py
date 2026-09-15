from odoo import api, fields, models


class TeqEsgMetric(models.Model):
    _name = "teq.esg.metric"
    _description = "TEQ ESG Metric"
    _inherit = ["mail.thread", "mail.activity.mixin"]
    _order = "date desc, category, name"

    name = fields.Char(required=True, tracking=True)
    date = fields.Date(default=fields.Date.context_today, required=True, tracking=True)
    category = fields.Selection(
        [
            ("environmental", "Environmental"),
            ("social", "Social"),
            ("governance", "Governance"),
        ],
        required=True,
        tracking=True,
    )
    value = fields.Float(required=True, tracking=True)
    unit = fields.Char(required=True)
    target = fields.Float(tracking=True)
    target_direction = fields.Selection(
        [("higher", "Higher is Better"), ("lower", "Lower is Better")],
        default="higher",
        required=True,
        tracking=True,
        help="Use Lower is Better for metrics such as emissions, waste, incidents, or energy intensity.",
    )
    performance = fields.Float(compute="_compute_performance", store=True)
    status = fields.Selection(
        [("on_track", "On Track"), ("watch", "Watch"), ("off_track", "Off Track")],
        compute="_compute_performance",
        store=True,
    )
    responsible_id = fields.Many2one(
        "res.users",
        default=lambda self: self.env.user,
        domain="[('share', '=', False), ('company_ids', 'in', company_id)]",
        tracking=True,
    )
    notes = fields.Html()
    company_id = fields.Many2one("res.company", default=lambda self: self.env.company, required=True)

    @api.depends("value", "target", "target_direction")
    def _compute_performance(self):
        for record in self:
            if not record.target:
                record.performance = 0.0
                record.status = "watch"
                continue

            if record.target_direction == "lower":
                if record.value <= 0:
                    record.performance = 100.0 if record.value <= record.target else 0.0
                else:
                    record.performance = (record.target / record.value) * 100.0
                if record.value <= record.target:
                    record.status = "on_track"
                elif record.value <= record.target * 1.2:
                    record.status = "watch"
                else:
                    record.status = "off_track"
            else:
                record.performance = (record.value / record.target) * 100.0
                if record.performance >= 100:
                    record.status = "on_track"
                elif record.performance >= 80:
                    record.status = "watch"
                else:
                    record.status = "off_track"
