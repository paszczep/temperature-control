from src.external_apis.drive_control import DriverCheck
from src.internal_apis.database_query import select_from_db, update_status_in_db
from src.internal_apis.models import ValuesSetting
from src.internal_processes.checking import CheckingSetting
from src.internal_processes.controlling import ControllingSetting
from src.internal_processes.driving import DrivingAction
from logging import info, warning
from decimal import Decimal
from typing import Union


class SettingDriving(ValuesSetting):
    container_name: str

    @staticmethod
    def _log_setting(value: Union[int, str, Decimal]) -> str:
        return DrivingAction.parse_temperature_value(value)

    def execute_setting_driver(self) -> list[DriverCheck]:
        info('setting running driver')
        return DrivingAction(
            container_name=self.container_name,
            temperature_setting=self.temperature).driver_check_and_introduce_setting()


class SettingProcess(SettingDriving):
    checking: CheckingSetting
    controlling: ControllingSetting

    def _log_container(self):
        _check = [c for c in self.checking.driver_checks if c.name == self.container_name].pop()
        info(f'setting check power:     {_check.power}')
        info(f'setting check logged:    {_check.logged}')
        info(f'setting check received:  {_check.received}')
        info(f'setting check set point: {self._log_setting(_check.setpoint)}')

    def end_set(self):
        info('setting process ended')
        self.status = 'ended'
        update_status_in_db(self)

    def prepare(self):
        self.temperature = Decimal(self.temperature)
        self.checking = CheckingSetting(self.id)
        self.container_name = self.checking.container
        info(f'setting - container: {self.container_name}, point: {self._log_setting(self.temperature)}')
        self.controlling = ControllingSetting(self.id)

    def execute_and_save_logs(self):
        self.checking.driver_checks = self.execute_setting_driver()
        self.checking.create_and_save_checks()
        self.controlling.save_set_control(self.temperature)
        self._log_container()

    def end_or_continue(self, setting_check: Decimal):
        info(f'setting - existing: {setting_check}, desired: {self._log_setting(self.temperature)}')
        if setting_check == self.temperature:
            info('setting desired and provided are equal, ending process.')
            self.end_set()
        else:
            info('setting process may be retried to verify')

    def run_and_check(self):
        info('setting process started')
        self.prepare()
        self.execute_and_save_logs()
        try:
            setting_check = self.checking.temperature_setting_verification()
        except ValueError:
            warning('setting no point for comparison, set may be retried')
        else:
            info('setting check found, proceeding')
            self.end_or_continue(setting_check)


class SettingExecution:
    @staticmethod
    def get_performed_set(set_id: str) -> SettingProcess:
        info('setting fetching parameters for execution')
        select_sets = select_from_db(table_name=ValuesSetting.__tablename__, where_equals={'id': set_id})
        if select_sets:
            info(f'setting selected')
            return [SettingProcess(**s) for s in select_sets].pop()
        else:
            warning('setting unavailable')
            pass

    def run_set(self, set_id: str):
        performed_set = self.get_performed_set(set_id)
        info(f'setting performed status: {performed_set.status}')

        if performed_set.status == 'running':
            performed_set.run_and_check()


def perform_setting(set_id: str):
    SettingExecution().run_set(set_id)
