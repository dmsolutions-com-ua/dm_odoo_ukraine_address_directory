{
    "name": "Ukraine Address Integration - Banks",
    "summary": "Geodata.online address autocomplete on the bank form · "
    "автозаповнення адрес України на банках, адресний довідник України, res.bank",
    "author": "DM Solutions",
    "website": "https://geodata.online",
    "category": "Accounting",
    "license": "LGPL-3",
    "version": "19.0.1.1.1",
    # Обкладинка модуля в Apps Store (без цього ключа магазин показує лише іконку).
    "images": ["static/description/cover.png"],
    # Bundled-bridge: тримається ядра (dm_geodata_connector), щоб парасолька
    # dm_geodata_online могла включити його у свій depends без циклу й доставити одним
    # zip з Apps Store. res.bank є в base, тож додаткових застосунків не тягне.
    # Знімається разом із ядром dm_geodata_connector.
    "depends": [
        "dm_geodata_connector",
    ],
    "data": [
        "views/res_bank_views.xml",
    ],
    "installable": True,
    "auto_install": True,
    "application": False,
}
