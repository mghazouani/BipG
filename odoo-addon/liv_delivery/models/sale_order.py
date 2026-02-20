# -*- coding: utf-8 -*-
from odoo import fields, models


class SaleOrder(models.Model):
    _inherit = "sale.order"

    x_delivery_id = fields.Many2one(
        "liv.delivery",
        string="Delivery Mission",
        ondelete="set null",
        copy=False,
    )
    x_payment_state = fields.Char(string="Payment State", copy=False)
    x_payment_method = fields.Char(string="Payment Method", copy=False)
    x_payment_ref = fields.Char(string="Payment Ref", copy=False)
    x_payment_ts = fields.Datetime(string="Payment At", copy=False)
