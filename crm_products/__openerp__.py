# -*- coding: utf-8 -*-
# Part of Abdallah Mohammed (<abdalla_mohammed@outlook.com>). See LICENSE file for full copyright and licensing details.

{
    'name': 'Products in Lead and Opportunity',
    'version': '1.0',
    'author': 'Abdallah Mohamed',
    'license': 'Other proprietary',
    'category': 'CRM',
    'website': 'abdalla_mohammed@outlook.com',
    'description': ''' 
This module add feature in Lead and Opportunity to appear expected product that customer need and update expected revenue and cost and probability based on "Calculate probability method" in every stage
  ''',
    'depends': ['base', 'product', 'crm'],
    'data': [
        'security/ir.model.access.csv',
        'views/crm_products.xml',
    ],
    'installable': True,
    'auto_install': False

}

# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:
