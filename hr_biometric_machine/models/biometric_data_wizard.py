# -*- coding: utf-8 -*-
##############################################################################
# For copyright and license notices, see __openerp__.py file in root directory
##############################################################################

from .biometric_data import BiometricData
from openerp import api, fields, models


class BiometricDataWizard(models.TransientModel):
    _name = 'biometric.data.wizard'

    biometric_device = fields.Many2one(
        'biometric.machine', 'Biometric device',
    )

    def import_attendance(self, cr, uid, ids, context):
        """
        wrapper function
        """
        for biometric_attendance in self.browse(cr, uid, ids, context):
            biometric_attendance.crate_attendance_in_openep()

    @api.model
    def crate_attendance_in_openep(self):
        """
        Call import function in biometric.data model
        """
        biometric_data_obj = self.env['biometric.data']
        biometric_user_obj = self.env['biometric.user']
        biometric_data_bio = biometric_data_obj.search([])
        BiometricData.convert_to_hr_attendance_classmethod(
            biometric_data_bio, biometric_data_obj,)
        biometric_machine = self.biometric_device
        BiometricData.import_data_classmethod(
            biometric_machine, biometric_data_obj, biometric_user_obj,)
