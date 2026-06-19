{
    "name": "Ukraine Address Integration - Banks",
    "summary": "Geodata.online address autocomplete on the bank form",
    "author": "DM Solutions",
    "website": "https://geodata.online",
    "category": "Accounting",
    "license": "LGPL-3",
    "version": "19.0.1.0.0",
    # Auto-install bridge: підключається, коли встановлено парасольку
    # (dm_geodata_online) — res.bank є в base; видалення dm_geodata_online прибирає його.
    "depends": [
        "dm_geodata_online",
    ],
    "data": [
        "views/res_bank_views.xml",
    ],
    "installable": True,
    "auto_install": True,
    "application": False,
}
