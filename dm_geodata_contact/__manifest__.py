{
    "name": "Ukraine Address Integration - Contacts",
    "summary": "Inline Geodata.online address autocomplete on contacts",
    "author": "DM Solutions",
    "website": "https://geodata.online",
    "category": "Hidden",
    "license": "LGPL-3",
    "version": "19.0.1.1.1",
    # Обкладинка модуля в Apps Store (без цього ключа магазин показує лише іконку).
    "images": ["static/description/cover.png"],
    # Bundled-bridge: тримається ядра (dm_geodata_connector), щоб парасолька
    # dm_geodata_online могла включити його у свій depends без циклу й доставити одним
    # zip з Apps Store. Auto-install лишається: підключається там, де є застосунок
    # «Контакти». Знімається разом із ядром dm_geodata_connector.
    "depends": [
        "dm_geodata_connector",
        "contacts",
    ],
    "data": [
        "views/res_partner_views.xml",
    ],
    "installable": True,
    "auto_install": True,
    "application": False,
}
