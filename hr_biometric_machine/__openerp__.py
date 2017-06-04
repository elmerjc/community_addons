# -*- coding: utf-8 -*-

{
    'name': 'Biometric Device Integration',
    'version': '1.2.1',
    'author': 'OpenPyme',
    'category': 'Payroll',
    'website': 'http://www.openpyme.mx',
    'license': 'GPL-3',
    'depends': ['hr_attendance'],
    'data': [
        'views/biometric_data_view.xml',
        'views/biometric_machine_view.xml',
        'views/hr_attendance.xml',
        'views/biometric_user_view.xml',
        'wizard/biometric_user.xml',
        'wizard/biometric_data.xml',
        'cron_task/biometric_data.xml',
    ],
    'installable': True,
    'external_dependencies': {
        'python': [
            'zk',
            'mock',
        ],
    },
}
