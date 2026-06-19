{
    "name": "Ukraine Address Integration - HR",
    "summary": "Geodata.online address autocomplete on the employee private address",
    "author": "DM Solutions",
    "website": "https://geodata.online",
    "category": "Human Resources",
    "license": "LGPL-3",
    "version": "19.0.1.0.0",
    # Auto-install bridge: підключається, коли встановлено і парасольку
    # (dm_geodata_online), і застосунок «Кадри»; видалення dm_geodata_online прибирає його.
    "depends": [
        "dm_geodata_online",
        "hr",
    ],
    "data": [
        "views/hr_employee_views.xml",
    ],
    "installable": True,
    "auto_install": True,
    "application": False,
}
