{
    "name": "Ukraine Address Integration - CRM",
    "summary": "Geodata.online address autocomplete on CRM leads/opportunities · "
    "автозаповнення адрес України у CRM, ліди й нагоди, адресний довідник України, "
    "crm.lead",
    "author": "DM Solutions",
    "website": "https://geodata.online",
    "category": "Sales/CRM",
    "license": "LGPL-3",
    "version": "19.0.1.0.1",
    # Обкладинка модуля в Apps Store (без цього ключа магазин показує лише іконку).
    "images": ["static/description/cover.png"],
    # Auto-install bridge: підключається, коли встановлено і парасольку
    # (dm_geodata_online), і CRM; видалення dm_geodata_online прибирає його.
    # Окремий лістинг Apps Store: bundling сюди примусово ставив би застосунок CRM.
    "depends": [
        "dm_geodata_online",
        "crm",
    ],
    "data": [
        "views/crm_lead_views.xml",
    ],
    "installable": True,
    "auto_install": True,
}
