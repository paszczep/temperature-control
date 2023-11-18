from src.internal_apis.database_query import update_status_in_db
from src.internal_processes.driving import DrivingAction
from src.external_processes.tasking_values import TaskingAttributes
from logging import info
from decimal import Decimal
from typing import Union


class TaskingExecute(TaskingAttributes):
    _intended_setting = Union[int, Decimal]

    @staticmethod
    def log_setting(point: Union[int, str, Decimal]) -> str:
        try:
            return DrivingAction.parse_temperature_value(point)
        except ValueError:
            return 'none found'

    def _log_task_execution(self):
        info(f'execute driver setting '
             f'temperature: {self.log_setting(self._intended_setting)} '
             f'in container: {self.checking.container_name}')

    def drive_setting_save_logs(self, execute_point: Union[int, Decimal]):
        self._intended_setting = execute_point
        self._log_task_execution()
        driver_ctrls = DrivingAction(
            container_name=self.checking.container_name,
            temperature_setting=self._intended_setting).driver_check_and_introduce_setting()
        self.checking.create_and_save_checks(driver_ctrls)
        self.controlling.save_task_control(self._intended_setting)

    def _log_consideration(self):
        info(f'execute '
             f'considering: {self.log_setting(self._intended_setting)}, '
             f'provided: {self.log_setting(self.checking.recent)}')

    def drive_consider_setting_save_log(self, execute_point: Union[int, Decimal]):
        self._intended_setting = execute_point
        self._log_consideration()
        if self._intended_setting != self.checking.recent:
            self.drive_setting_save_logs(self._intended_setting)
        else:
            info('execute desired setting active')
            self.controlling.save_task_control(self._intended_setting)

    def drive_error_task(self):
        info('execute error')
        self.task.status = 'error'
        update_status_in_db(self.task)

    def drive_end_task(self):
        info('execute ending')
        self.task.status = 'ended'
        update_status_in_db(self.task)

    def driver_check_containers(self):
        info('execute checking for benchmark')
        self.checking.driver_check_containers()
