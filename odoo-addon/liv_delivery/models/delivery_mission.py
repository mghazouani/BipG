# -*- coding: utf-8 -*-
from odoo import api, fields, models


class LivDelivery(models.Model):
    _name = "liv.delivery"
    _description = "Delivery Mission"
    _order = "id desc"
    _inherit = ["mail.thread", "mail.activity.mixin"]

    name = fields.Char(required=True, copy=False, readonly=True, default="New")
    customer_name = fields.Char(required=True, tracking=True)
    customer_phone = fields.Char(tracking=True)
    address = fields.Char(required=True, tracking=True)
    lat = fields.Float(tracking=True)
    lon = fields.Float(tracking=True)
    driver_id = fields.Many2one("res.users", string="Driver", tracking=True)
    state = fields.Selection(
        [
            ("draft", "Draft"),
            ("assigned", "Assigned"),
            ("en_route", "En Route"),
            ("arrived", "Arrived"),
            ("delivered", "Delivered"),
            ("cancelled", "Cancelled"),
        ],
        default="draft",
        required=True,
        tracking=True,
    )
    active = fields.Boolean(default=True)
    last_lat = fields.Float(readonly=True)
    last_lon = fields.Float(readonly=True)
    last_ts = fields.Char(readonly=True)
    track_ids = fields.One2many(
        "liv.delivery.track",
        "delivery_id",
        string="Tracking Snapshots",
        readonly=True,
    )
    sale_order_id = fields.Many2one(
        "sale.order",
        string="Sale Order",
        ondelete="set null",
        index=True,
    )

    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            if vals.get("name") in (None, "New", False):
                vals["name"] = self.env["ir.sequence"].next_by_code("liv.delivery") or "New"
        return super().create(vals_list)

    def action_assign(self):
        for rec in self:
            if rec.state != "draft":
                continue
            if not rec.driver_id:
                continue
            rec.state = "assigned"

    def action_start(self):
        for rec in self:
            if rec.state != "assigned":
                continue
            rec.state = "en_route"

    def action_arrive(self):
        for rec in self:
            if rec.state != "en_route":
                continue
            rec.state = "arrived"

    def action_deliver(self):
        for rec in self:
            if rec.state not in ("en_route", "arrived"):
                continue
            rec.state = "delivered"

    def action_cancel(self):
        for rec in self:
            if rec.state in ("delivered", "cancelled"):
                continue
            rec.state = "cancelled"
