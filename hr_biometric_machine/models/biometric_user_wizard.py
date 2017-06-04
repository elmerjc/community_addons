# -*- coding: utf-8 -*-
##############################################################################
# For copyright and license notices, see __openerp__.py file in root directory
##############################################################################

from openerp import api, fields, models


class BiometricUser(models.TransientModel):
    _name = 'biometric.user.wizard'

    biometric_device = fields.Many2one(
        'biometric.machine', 'Biometric device',
    )

    def import_users(self, cr, uid, ids, context):
        """
        wrapper function
        """
        for biometric_import_user in self.browse(cr, uid, ids, context):
            biometric_import_user.create_users_in_openerp()

    @api.model
    def create_users_in_openerp(self):
        self.biometric_device.create_user()
