{
    "name": "Issabel Connector - Real Time Statistics",
    "version": "18.0.2.0.0",
    "category": "Tools",
    "summary": "Integración con Asterisk/Issabel para estadísticas en tiempo real",
    "description": """
        Issabel/Asterisk Connector con Estadísticas en Tiempo Real
        ===========================================================
        
        Características:
        ----------------
        * Conexión AMI (Asterisk Manager Interface) en tiempo real
        * Estadísticas de colas en vivo
        * Monitoreo de agentes (disponibles, en llamada, pausados)
        * Llamadas en espera con tiempos de espera
        * Registro histórico de llamadas
        * Dashboard interactivo con actualización en tiempo real
        * Nivel de servicio (SLA) en tiempo real
        * Arquitectura frontend modular con patrones de diseño
        
        Eventos capturados:
        ------------------
        * QueueParams: Estadísticas generales de colas
        * QueueMember: Estado de agentes
        * QueueEntry: Llamadas en espera
        * QueueCallerJoin/Leave/Abandon: Movimientos en colas
        * AgentConnect/Complete: Conexiones de agentes
        * NewChannel/Hangup: Gestión de llamadas
        
        Arquitectura Frontend:
        ---------------------
        * Patrón Strategy para handlers de eventos
        * Patrón Registry para gestión de handlers
        * Patrón Template Method para flujo consistente
        * Patrón Facade para API simplificada
        * Separation of Concerns (UI, lógica, datos)
        * Código testeable y extensible
    """,
    "author": "Tu Empresa",
    "website": "https://www.fenalcovalle.com",
    "license": "LGPL-3",
    "depends": ["base", "web", "queue_job", "bus","voip"],
    "data": [
        # Seguridad
        "security/ir.model.access.csv",
        # Datos iniciales
        "data/queue_job_channel.xml",
        "data/queue_job_cleanup_cron.xml",
        # Vistas principales
        "views/issabel_config_views.xml",
        "views/issabel_voip_call_view.xml",
        # Menús
        "views/issabel_menus.xml",
    ],
    "assets": {
        "web.assets_backend": [
            "issabel_connector/static/src/services/event_handlers/base.js",
            "issabel_connector/static/src/services/event_handlers/call_handlers.js",
            "issabel_connector/static/src/services/event_handlers/agent_handlers.js",
            "issabel_connector/static/src/services/event_handlers/queue_handlers.js",
            "issabel_connector/static/src/services/event_handlers/event_processor.js",
            "issabel_connector/static/src/components/issabel_dashboard/issabel_dashboard.js",
            "issabel_connector/static/src/components/issabel_dashboard/issabel_dashboard.xml",
            "issabel_connector/static/src/components/issabel_dashboard/issabel_dashboard.scss",
        ],
    },
    "external_dependencies": {
        "python": ["asterisk-ami", "panoramisk"],
    },
    "installable": True,
    "application": True,
    "auto_install": False,
   
}
