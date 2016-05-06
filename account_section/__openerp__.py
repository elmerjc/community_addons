# -*- coding: utf-8 -*-

{
    'name': 'Account section',
    'version': '0.1',
    'category': 'Accounting',
    'description': '''Associate a purchase account and sale account to a sale department.
    This account is used on invoice generation.
    ''',
    'author': 'Elneo',
    'website': 'http://www.elneo.com',
    'depends': ['account','purchase','sales_team','stock_account'],
    "data" : ['views/account_section_view.xml'],
    'installable': True,
    'auto_install': False,
    'application': False,
}
