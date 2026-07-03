{
    "name": "Asertis WhatsApp Templates",
    "version": "1.0",
    "category": "Tools",
    "summary": "Plantillas de WhatsApp personalizables con parámetros dinámicos para CRM",
    "description": """
Asertis WhatsApp Templates
==========================

Módulo de integración de WhatsApp con plantillas personalizables para Odoo CRM.

Características Principales:
* Crear y gestionar plantillas de mensajes WhatsApp
* Sistema de parámetros dinámicos usando cualquier campo de modelos Odoo
* Envío de mensajes directamente desde leads y oportunidades CRM
* Gestión de plantillas similar a plantillas de correo electrónico
* Historial completo y seguimiento de mensajes
* Capa de integración API para WhatsApp Business API
* Soporte multi-empresa
* Validación y formateo de números telefónicos

Características Técnicas:
* Sistema de parámetros de plantilla con selección de campos de cualquier modelo
* Endpoints API configurables y credenciales
* Registro de mensajes y manejo de errores
* Grupos de seguridad y control de acceso
* Integración con flujos de trabajo CRM existentes
* Soporte para diferentes tipos de plantillas WhatsApp (texto, medios, botones)

Uso:
1. Configurar ajustes API en Configuraciones Técnicas
2. Crear plantillas WhatsApp con parámetros dinámicos
3. Usar botón WhatsApp en leads CRM para enviar mensajes
4. Rastrear todas las comunicaciones en historial de mensajes

Compatible con WhatsApp Business API a través de API intermedia personalizada.
    """,
    "author": "Fenalco Valle",
    "website": "https://asertis.com.co/",
    "license": "LGPL-3",
    "depends": [
        "base",
        "crm",
        "contacts",
    ],
    "external_dependencies": {
        "python": ["requests"],
    },
    "data": [
        "security/ir.model.access.csv",
        "views/whatsapp_asertis_config_views.xml",
        "views/whatsapp_asertis_template_views.xml",
        "views/whatsapp_asertis_template_param_views.xml",
        "views/whatsapp_asertis_message_log_views.xml",
        "views/whatsapp_asertis_template_send_wizard_views.xml",
        "views/wizard_multirecord_view.xml", 
        "views/crm_lead_view_tree_inherit.xml",
        "views/menu.xml",
    ],
    "assets": {
        "web.assets_backend": [
            "asertis_whatsapp_templates/static/src/scss/*.scss",
            "asertis_whatsapp_templates/static/src/**/web/**/*",
        ],
    },
    "installable": True,
    "application": False,
    "auto_install": False,
}
