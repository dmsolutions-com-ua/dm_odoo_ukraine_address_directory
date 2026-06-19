{
    "name": "Ukraine Address Integration - Contacts",
    "summary": "Inline Geodata.online address autocomplete on contacts",
    "author": "DM Solutions",
    "website": "https://geodata.online",
    "category": "Hidden",
    "license": "LGPL-3",
    "version": "19.0.1.0.0",
    # Auto-install bridge: підключається, коли встановлено і парасольку
    # (dm_geodata_online), і застосунок «Контакти»; видалення dm_geodata_online прибирає його.
    "depends": [
        "dm_geodata_online",
        "contacts",
    ],
    "data": [
        "views/res_partner_views.xml",
    ],
    "installable": True,
    "auto_install": True,
    "application": False,
}
