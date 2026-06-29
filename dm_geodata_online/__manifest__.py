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
    "version": "19.0.1.1.0",
    # Обкладинка модуля в Apps Store (без цього ключа магазин показує іконку).
    "images": ["static/description/cover.png"],
    # Парасольковий застосунок. Один zip з Apps Store доставляє ядро й легкі bridge
    # (contact/company/bank — base-моделі, не тягнуть важких застосунків), тож підказки
    # на контактах/компаніях/банках працюють «з коробки». Ці bridge тримаються ядра
    # dm_geodata_connector (тут лише форвард-залежність, без циклу) і знімаються разом
    # із ядром. Bridge для CRM/HR/Lunch навмисно сюди не входять: їхній depends на
    # crm/hr/lunch примусово ставив би ці застосунки всім — вони лишаються окремими
    # auto_install-лістингами Apps Store для відповідних застосунків.
    "depends": [
        "dm_geodata_connector",
        "dm_geodata_contact",
        "dm_geodata_company",
        "dm_geodata_bank",
    ],
    "data": [],
    "installable": True,
    "auto_install": False,
    "application": True,
}
