{
    "name": "Reference Directory of Ukrainian Addresses",
    "summary": "Geodata.online address autocomplete · Адресний довідник України "
    "довідник адрес України адреси України база адрес України актуальні "
    "адреси України автозаповнення адрес України address autocomplete "
    "address database Ukraine",
    "author": "DM Solutions",
    "website": "https://geodata.online",
    "category": "Extra Tools",
    "license": "LGPL-3",
    "version": "19.0.1.0.1",
    # Обкладинка модуля в Apps Store (без цього ключа магазин показує іконку).
    "images": ["static/description/cover.png"],
    # Парасольковий застосунок: його встановлення підтягує ядро й дозволяє
    # auto_install-бриджам (dm_geodata_contact/crm/company) підключитися там, де є
    # відповідний застосунок. Видалення каскадно прибирає ці бриджі (ядро
    # dm_geodata_connector лишається — видаляється окремо для повного прибирання).
    "depends": [
        "dm_geodata_connector",
    ],
    "data": [],
    "installable": True,
    "auto_install": False,
    "application": True,
}
