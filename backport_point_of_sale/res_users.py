
import math

from openerp.osv import osv, fields

import openerp.addons.product.product


class res_users(osv.osv):
    _inherit = 'res.users'
    _columns = {
        'ean13' : fields.char('EAN13', size=13, help="BarCode"),
        'pos_security_pin': fields.char('Security PIN',size=32, help='A Security PIN used to protect sensible functionality in the Point of Sale'),
        'pos_config' : fields.many2one('pos.config', 'Default Point of Sale', domain=[('state', '=', 'active')]),
    }

    def _check_ean(self, cr, uid, ids, context=None):
        return all(
            openerp.addons.product.product.check_ean(user.ean13) == True
            for user in self.browse(cr, uid, ids, context=context)
        )

    _constraints = [
        (_check_ean, "Error: Invalid ean code", ['ean13'],),
    ]

