{
    "name": "Ukraine Address Reference Directory",
    "summary": "Integration with Geodata.online API for address autocomplete and "
    "normalization in Ukraine (self-contained, Odoo 19) · ядро інтеграції з API "
    "Geodata.online, автозаповнення та нормалізація адрес України, адресний довідник "
    "України, dm.geodata.address.mixin",
    "author": "DM Solutions",
    "website": "https://geodata.online",
    "category": "Hidden",
    "license": "LGPL-3",
    "version": "19.0.1.1.3",
    "depends": [
        "base",
        "base_geolocalize",
        "web",
    ],
    "external_dependencies": {
        "python": ["requests"],
    },
    "data": [
        "security/geodata_security.xml",
        "security/ir.model.access.csv",
        "security/geodata_record_rules.xml",
        "data/base_geo_provider.xml",
        "data/geodata_request_log_cron.xml",
        "data/geodata_health_cron.xml",
        "views/geodata_api_credential_views.xml",
        "views/geodata_address_views.xml",
        "views/geodata_request_log_views.xml",
    ],
    "demo": [],
    "assets": {
        "web.assets_backend": [
            "dm_geodata_connector/static/src/js/geodata_autocomplete_field.js",
            "dm_geodata_connector/static/src/xml/geodata_autocomplete_field.xml",
            "dm_geodata_connector/static/src/scss/geodata_autocomplete.scss",
        ],
    },
    "installable": True,
    "auto_install": False,
    "application": False,
    "post_init_hook": "post_init_hook",
    # Обкладинка модуля в Apps Store (без цього ключа магазин показує лише іконку).
    "images": [
        "static/description/cover.png",
    ],
}
