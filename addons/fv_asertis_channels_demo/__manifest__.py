# -*- coding: utf-8 -*-
{
    'name': "Asertis Demos Dash",

    'summary': "Short (1 phrase/line) summary of the module's purpose",

    'description': """
Long description of module's purpose
    """,

    'author': "Fenalco Valle",
    'website': "https://www.yourcompany.com",
    'icon': '/fv_asertis_channels_demo/static/src/img/icon.svg',  
    # Categories can be used to filter modules in modules listing
    # Check https://github.com/odoo/odoo/blob/15.0/odoo/addons/base/data/ir_module_category_data.xml
    # for the full list
    'category': 'Uncategorized',
    'version': '0.1',

    # any module necessary for this one to work correctly
    'depends': ['base','mail'],  

    # always loaded
    'data': [
        # 'security/ir.model.access.csv',
        'views/views.xml',
        'views/templates.xml',

        'views/demo_iframe_dash.xml',
    ],  
    # only loaded in demonstration mode
    'demo': [
        'demo/demo.xml',
    ],

     'assets': {
        
        'web.assets_backend': [
            'fv_asertis_channels_demo/static/src/components/**/*.xml',
            'fv_asertis_channels_demo/static/src/components/**/*.js',
            'fv_asertis_channels_demo/static/src/components/**/*.scss',
            #'odoo_custom_dashboard/static/src/components/dash_info_general/*.js',
            #'odoo_custom_dashboard/static/src/components/dash_info_general/*.xml',
          

        ],   
    }, 

}

