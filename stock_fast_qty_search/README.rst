.. image:: https://img.shields.io/badge/licence-AGPL--3-blue.svg
    :alt: License: AGPL-3

Fast product quantities search
==============================

Currently search product by quantity is verry slow.
With this module search time is divided by ~ 200 (tested on 80k products).
For 80K products in databases, search product by quantity 
take ~ 6.6 mn (400 second). So odoo, compute quantities for each product and 
make filter in python side.
With this module product are filtred in one SQL request executed in 2 seconds.


Bug Tracker
===========

Bugs are tracked on `GitHub Issues <https://github.com/OCA/stock-logistics-workflow/issues>`_.
In case of trouble, please check there if your issue has already been reported.
If you spotted it first, help us smashing it by providing a detailed and welcomed feedback.


Credits
=======

Contributors
------------

* Mourad EL HADJ MIMOUNE <mourad.elhadj.mimoune@akretion.com>



Maintainer
----------

.. image:: http://odoo-community.org/logo.png
   :alt: Odoo Community Association
   :target: http://odoo-community.org

This module is maintained by the OCA.

OCA, or the Odoo Community Association, is a nonprofit organization whose mission is to support the collaborative development of Odoo features and promote its widespread use.

To contribute to this module, please visit http://odoo-community.org.

