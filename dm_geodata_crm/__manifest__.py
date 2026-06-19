{
    "name": "Ukraine Address Integration - CRM",
    "summary": "Geodata.online address autocomplete on CRM leads/opportunities",
    "author": "DM Solutions",
    "website": "https://geodata.online",
    "category": "Sales/CRM",
    "license": "LGPL-3",
    "version": "19.0.1.0.0",
    # Auto-install bridge: підключається, коли встановлено і парасольку
    # (dm_geodata_online), і CRM; видалення dm_geodata_online прибирає його.
    "depends": [
        "dm_geodata_online",
        "crm",
    ],
    "data": [
        "views/crm_lead_views.xml",
    ],
    "installable": True,
    "auto_install": True,
}
