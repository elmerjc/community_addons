# coding: utf-8
{
    'name': "Product Serial Unique Number",
    'author': "Vauxoo",
    'website': "http://www.vauxoo.com",
    'category': 'stock',
    'version': '8.0.0.1.0',
    'license': "AGPL-3",
    'depends': ['stock_no_negative'],
    'data': [
        "views/product_view.xml",
        "views/stock_view.xml",
        "views/stock_serial_view.xml",
    ],
    'demo': [
        "demo/test_demo.xml",
    ],
    'installable': True,
    'auto_install': False,
}
