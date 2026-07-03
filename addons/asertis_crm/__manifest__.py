# -*- coding: utf-8 -*-

{
    'name': 'CRM Asertis',
    'version': '1.0',
    'category': 'Sales/CRM',
    'summary': 'Seguimiento para los leads comerciales de Asertis',
    'website': 'https://fenalcovalle.com',
    "license": "LGPL-3",
    'depends': ['base', 'mail'],
    'data': [
        # Security
        'security/security.xml',
        'security/groups.xml',
        'security/perm_group_asesores.xml',

        # Data
        'data/data_crm_asertis_stages.xml',

        # Views
        'views/crm_asertis.xml',
        'views/crm_asertis_clientes.xml',
        'views/crm_asertis_menu_config.xml',
        'views/crm_asertis_servicios.xml',
        'views/crm_asertis_stages.xml',
        'views/crm_asertis_metas.xml',
        'views/inherit_res_users.xml',

        # Componentes Owl
        'views/owl_crm_main.xml',
        

        # Wizard
        'wizard/crm_asertis_actividades_wiz.xml'
    ],
    'demo': [
        
    ],
    'installable': True,
    'application': True,
    'assets': {
        "web.assets_backend": [
            "asertis_crm/static/src/components/**/*.js",
            "asertis_crm/static/src/components/**/*.xml",
            "asertis_crm/static/src/components/**/*.css",
            "asertis_crm/static/src/js/**/*.js",
        ],
    },
}
