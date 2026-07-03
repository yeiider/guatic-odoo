{
    "name": "Asertis Canales Digitales",
    "version": "1.0",
    "depends": ["base", "mail", "contacts", "queue_job"],
    "author": "Fenalco Valle ",
    "category": "Tools",
    "website": "https://asertis.com.co/",
    "license": "LGPL-3",
    "summary": "Integración de Proveedor Chat con mensajes directos en Odoo",
    "installable": True,
    "application": False,
    "data": [
        "security/ir.model.access.csv",
        "data/chat_channel_type.xml",
        "views/chat_provider_views.xml",
        "views/provider_skill_views.xml",
        "views/partner_skill_views.xml",
        "views/provider_skill_import_wizard.xml",
        "views/menu.xml",
    ],
    "assets": {
        "web.assets_backend": [
            "asertis_canales_digitales/static/src/services/chat_history_service.js",
            "asertis_canales_digitales/static/src/components/history_message/history_message.js",
            "asertis_canales_digitales/static/src/components/history_message/history_message.xml",
            "asertis_canales_digitales/static/src/components/chat_history_panel/chat_history_panel.js",
            "asertis_canales_digitales/static/src/components/chat_history_panel/chat_history_panel.xml",
            "asertis_canales_digitales/static/src/components/chat_history_panel/chat_history_panel.scss",
            "asertis_canales_digitales/static/src/core/web/thread_actions_registry.js",
            "asertis_canales_digitales/static/src/components/discuss/discuss.js",
        ]
    },
    "post_init_hook": "assign_uuids_to_old_messages",
}
