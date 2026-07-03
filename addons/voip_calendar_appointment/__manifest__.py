{
    'name': 'VoIP Calendar Appointment',
    'version': '18.0.1.0.0',
    'category': 'Productivity',
    'summary': 'Integración entre VoIP y Calendar para agendar citas',
    'description': """
        Este módulo permite agendar citas directamente desde las llamadas VoIP
        hacia el módulo de calendario de Odoo.
        
        Características:
        - Botón de agendar cita en las vistas de llamadas VoIP
        - Integración automática con el calendario
        - Contexto automático del usuario y contacto
        - Acceso desde menú de más opciones
    """,
    'author': 'Tu Empresa',
    'website': 'https://www.tuempresa.com',
    'depends': ['base', 'voip', 'calendar', 'mail'],
    'data': [
        'security/ir.model.access.csv',
        
        'views/calendar_event_views.xml',
        
    ],
    'assets': {
        'web.assets_backend': [
            'voip_calendar_appointment/static/src/js/voip_calendar.js',
            'voip_calendar_appointment/static/src/css/voip_calendar.css',
        ],
    },
    'installable': True,
    'auto_install': False,
    'application': False,
    'license': 'LGPL-3',
}
