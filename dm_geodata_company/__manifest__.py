{
    "name": "Ukraine Address Integration - Companies",
    "summary": "Geodata.online address autocomplete on the company form",
    "author": "DM Solutions",
    "website": "https://geodata.online",
    "category": "Extra Tools",
    "license": "LGPL-3",
    "version": "19.0.1.0.0",
    # Auto-install bridge: підключається, коли встановлено парасольку
    # (dm_geodata_online) — res.company є в base; видалення dm_geodata_online прибирає його.
    "depends": [
        "dm_geodata_online",
    ],
    "data": [
        "views/res_company_views.xml",
    ],
    "installable": True,
    "auto_install": True,
}
