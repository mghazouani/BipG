{
    "name": "LIV Delivery Tracking",
    "version": "1.2",
    "depends": ["base", "sale", "mail"],
    "data": [
        "data/sequence.xml",
        "data/backend_health_cron.xml",
        "security/ir.model.access.csv",
        "views/delivery_views.xml",
        "views/delivery_mission_views.xml",
        "views/backend_health_views.xml",
    ],
    "installable": True,
    "license": "LGPL-3",
}
