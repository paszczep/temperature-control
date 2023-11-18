from src.internal_processes.controlling import InvalidSettingRetry
from src.external_processes.tasking_decide import TaskingDecide
from logging import info, warning
from decimal import Decimal
# from typing import Union
# from time import time


SETTING_RETRY_LIMIT = 5


class TaskingVerify(TaskingDecide):
    _checks: list[Decimal]
    _controls: list[Decimal]

    def _log_setting_points(self, points: list[Decimal]) -> str:
        return ' -> '.join(self.log_setting(p) for p in points)

    def _retrieve_verification_points(self):
        self._controls = [ctrl for ctrl in self.controlling.settings]
        info(f'verify controls: {self._log_setting_points(self._controls[::-1])}')
        self._checks = [
            Decimal(chk.read_setpoint) for chk in self.checking.checks
            if chk.timestamp > self.task.start and chk.read_setpoint]
        info(f'verify checks:   {self._log_setting_points(self._checks[::-1])}')

    def _verify_check_availability(self):
        no_set_point = [
            chk for chk in self.checking.checks
            if chk.read_setpoint == '']
        for point in no_set_point:
            info(f'verify no check point {point.get_log_info()}')
        if len(no_set_point) == SETTING_RETRY_LIMIT:
            raise InvalidSettingRetry

    def verify_control_execution(self):
        info('verify control execution')
        self._verify_check_availability()
        self._retrieve_verification_points()
        if len(self._controls) >= SETTING_RETRY_LIMIT:
            control_mismatched = [control for control in self._controls if control not in self._checks]
            info(f'verify setting mismatches: {self._log_measures(control_mismatched)}')
            if len(control_mismatched) >= SETTING_RETRY_LIMIT:
                if len(set(self._controls[:SETTING_RETRY_LIMIT])) == 1:
                    warning(f'{SETTING_RETRY_LIMIT} settings repeated to no effect. Raising error')
                    raise InvalidSettingRetry

    def verify_previous_setting(self):
        control = self.controlling.recent
        check = self.checking.recent
        info(f'verify control point: {self.log_setting(control)}')
        info(f'verify check point:   {check}')
        if control != check:
            info('verify retrying previous setting')
            self.drive_setting_save_logs(control)
            raise StopIteration
        else:
            info('verify setting pass')
            pass
