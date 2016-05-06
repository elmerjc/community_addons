# -*- coding: utf-8 -*-

{
    'name': 'Maintenance',
    'version': '0.1',
    'category': 'Maintenance',
    'description': "Module to manage maintenance.",
    'author': 'Elneo',
    'website': 'http://www.elneo.com',
    'depends': ['base','product', 'sale'],
    'data': ['security/maintenance_security.xml',
             'maintenance_view.xml',
             'maintenance_sequence.xml', 
             'security/ir.model.access.csv', 
             'installation_workflow.xml',
             'report/report_maintenance.xml',
             'report/maintenance_report.xml',
             'res_config.xml'],
    'installable': True,
    'active': False,
    'application':True
}
