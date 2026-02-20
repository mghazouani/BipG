# -*- coding: utf-8 -*-
from odoo import models, fields


class LivDeliveryTrack(models.Model):
    _name = "liv.delivery.track"
    _description = "Delivery Tracking Snapshot"
    _order = "id desc"

    delivery_id = fields.Many2one(
        "liv.delivery",
        string="Delivery",
        required=True,
        ondelete="cascade",
        index=True,
    )
    driver_id = fields.Many2one("res.users", string="Driver", ondelete="set null")
    lat = fields.Float(required=True)
    lon = fields.Float(required=True)
    ts = fields.Char(required=True)
