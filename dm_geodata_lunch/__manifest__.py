{
    "name": "Ukraine Address Integration - Lunch",
    "summary": "Geodata.online address autocomplete on the lunch supplier form",
    "author": "DM Solutions",
    "website": "https://geodata.online",
    "category": "Extra Tools",
    "license": "LGPL-3",
    "version": "19.0.1.0.0",
    # Auto-install bridge: підключається, коли встановлено й парасольку
    # (dm_geodata_online), і сам модуль `lunch`. Видалення будь-якого з них прибирає його.
    "depends": [
        "dm_geodata_online",
        "lunch",
    ],
    "data": [
        "views/lunch_supplier_views.xml",
    ],
    "installable": True,
    "auto_install": True,
}
