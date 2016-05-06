# -*- coding: utf-8 -*-

{
    'name': 'Maintenance Product',
    'version': '0.1',
    'category': 'Maintenance Product',
    'description': "Module to manage products of maintenance.",
    'author': 'Elneo',
    'website': 'http://www.elneo.com',
    'depends': ['maintenance', 'sale','stock_account','stock','account_section','account'],
    'data': ['wizard/maintenance_update_view.xml',
             'maintenance_product_view.xml',
                   'maintenance_product_sequence.xml', 
                   'security/ir.model.access.csv',
                   'report/report_maintenance.xml', 
                   'data/stock_picking.yml',
                   'res_config.xml'
                   ],
    'installable': True,
    'active': False,
    'application':False
}
