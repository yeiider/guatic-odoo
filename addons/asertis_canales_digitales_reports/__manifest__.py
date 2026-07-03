{
    "name": "Repotería Asertis Canales Digitales",
    "version": "1.0",
    "depends": ["base", "web"],
    "author": "Fenalco Valle",
    "category": "Tools",
    "website": "https://asertis.com.co/",
    "license": "LGPL-3",
    "summary": "Modulo de reporteria de  los canales digitales para aseritis",
    "installable": True,
    "application": False,
    "data": [
        "security/ir.model.access.csv",
        "data/cron_data.xml",
        "views/api_config_view.xml",
        "views/dashboard_template.xml",
        "views/menu_view.xml",
    ],
    "assets": {
        "web.assets_backend": {
            "asertis_canales_digitales_reports/static/src/js/lib/chart.min.js",
            "asertis_canales_digitales_reports/static/src/js/dashboard.js",
            "asertis_canales_digitales_reports/static/src/css/dashboard.css",
        }
    },
}
