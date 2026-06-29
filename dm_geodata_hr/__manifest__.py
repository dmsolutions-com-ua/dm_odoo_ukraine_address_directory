{
    "name": "Ukraine Address Integration - HR",
    "summary": "Geodata.online address autocomplete on the employee private address · "
    "автозаповнення адрес України у Кадрах, приватна адреса працівника, "
    "адресний довідник України, hr.employee",
    "author": "DM Solutions",
    "website": "https://geodata.online",
    "category": "Human Resources",
    "license": "LGPL-3",
    "version": "19.0.1.0.1",
    # Обкладинка модуля в Apps Store (без цього ключа магазин показує лише іконку).
    "images": ["static/description/cover.png"],
    # Auto-install bridge: підключається, коли встановлено і парасольку
    # (dm_geodata_online), і застосунок «Кадри»; видалення dm_geodata_online прибирає його.
    # Окремий лістинг Apps Store: bundling сюди примусово ставив би застосунок «Кадри».
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
