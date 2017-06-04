# -*- coding: utf-8 -*-

from zk.attendance import Attendance
from zk import ZK


class ZkOpenerp(ZK):

    def get_attendance(self):
        attendaces = super(ZkOpenerp, self).get_attendance()
        attendaces_openerp = []
        for attendace in attendaces:
            attendace_openerp = OpenerpAttendance(
                attendace.user_id, attendace.timestamp, attendace.status)
            attendaces_openerp.append(attendace_openerp)
        return attendaces_openerp


class OpenerpAttendance(Attendance):

    @property
    def action_perform(self):
        actions = {
            0: 'sign_in',
            1: 'sign_out',
        }
        return actions.get(self.status)
