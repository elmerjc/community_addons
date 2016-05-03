# -*- coding: utf-8 -*-
##############################################################################
#
#    OpenERP, Open Source Management Solution
#    Copyright (C) 2014 Akretion (<http://www.akretion.com>).
#
#    This program is free software: you can redistribute it and/or modify
#    it under the terms of the GNU Affero General Public License as
#    published by the Free Software Foundation, either version 3 of the
#    License, or (at your option) any later version.
#
#    This program is distributed in the hope that it will be useful,
#    but WITHOUT ANY WARRANTY; without even the implied warranty of
#    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#    GNU Affero General Public License for more details.
#
#    You should have received a copy of the GNU Affero General Public License
#    along with this program.  If not, see <http://www.gnu.org/licenses/>.
#
##############################################################################

{
    'name': 'POS MRP product operation',
    'version': '0.1',
    'author': 'Akretion',
    'depends': [
        'point_of_sale',
        'pos_product_template',
        'mrp_product_operation',
    ],
    'demo': [],
    'website': 'https://www.akretion.com',
    'description': """
        This module allow to add MRP operation to
        a product sold in the POS.
    """,
    'data': [
        'views/pos_mrp_product_operation.xml',
    ],
    'qweb': [
        'static/src/xml/pos_mrp_product_operation.xml',
    ],
    'test': [],
    'installable': True,
    'auto_install': False,
}

# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:
