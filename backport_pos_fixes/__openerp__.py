{
    'name': 'Backport POS Fixes',
    'summary': 'Point of Sale Fixes',
    'describtion': """
    Fixes included:
    - Fix POS invoices payments by reconciling them automatically on POS session closing to get them paid.
    - Complete the anglo-saxon journal entries missing in POS.
    *ToDo*:
        - Handle UoS convertion ex. selling in grams while product UoS is KG .
     """,
    'version': '8.0.0.2',
    'category': 'Point of Sale',
    'author': 'DVIT.me',
    'website': 'http://dvit.me',
    'license': 'AGPL-3',
    'depends': [
        'account_anglo_saxon',
        'account',
        'account_voucher',
        'backport_point_of_sale',
    ],
    'data': [],
    'demo': [],
    'installable': True,
    'auto_install': False,
    'application': False,
}
