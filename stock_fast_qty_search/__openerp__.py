# -*- coding: utf-8 -*-
# © 2014-2016 Akretion (http://www.akretion.com)
#   @author Mourad EL HADJ MIMOUNE <mourad.elhadj.mimoune@akretion.com>
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl.html).
{
    'name': 'Fast products quantity search',
    'summary': """Currently search product by quantity is verry slow.
    With this module search time is divided by ~ 200 (tested on 80k products).
        """,
    'version': '8.0.0.1.0',
    'author': "Akretion,Odoo Community Association (OCA)",
    'website': 'http://www.akretion.com',
    'category': 'Warehouse',
    'depends': [
        'stock',
        'product',
    ],
    'application': False,
    'installable': True,
}

