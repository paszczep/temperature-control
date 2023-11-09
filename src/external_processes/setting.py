from src.external_apis.drive import DriveCtrl
from src.internal_apis.database_query import select_from_db, update_status_in_db
from src.internal_apis.models_data import SettingTask
from src.internal_processes.checking import CheckingSetting
from src.internal_processes.controlling_new import ControllingSetting
from src.internal_processes.driving import DrivingAction
from logging import info, warning
from typing import Union
from decimal import Decimal


class SettingDriving(SettingTask):
    container_name: str

    def execute_setting_driver(self) -> list[DriveCtrl]:
        info('running setting of temperature')
        return DrivingAction(
            process_id=self.id,
            container_name=self.container_name,
            temperature_setting=self.temperature).driver_check_and_introduce_setting()


class SettingProcess(SettingDriving):

    def end_set(self):
        info('setting process ended')
        self.status = 'ended'
        update_status_in_db(self)

    def run_and_check(self):
        info('setting process ended')

        checking = CheckingSetting(self.id)
        controlling = ControllingSetting(self.id)

        self.container_name = checking.container
        checking.driver_ctrls = self.execute_setting_driver()
        checking.create_and_save_checks()
        controlling.save_set_control(self.temperature)
        setting_check = checking.temperature_setting_verification()

        info(f'settings - existing: {setting_check}, desired: {self.temperature}')
        if setting_check == Decimal(self.temperature):
            info('desired and provided settings are equal, ending process.')
            self.end_set()
        else:
            info('process will be retried to verify setting.')


class SettingExecution:
    @staticmethod
    def get_performed_set(set_id: str) -> SettingProcess:
        info('fetching setting parameters for execution')
        select_sets = select_from_db(table_name=SettingTask.__tablename__, where_equals={'id': set_id})
        if select_sets:
            info(f'selected setting')
            return [SettingProcess(**s) for s in select_sets].pop()
        else:
            warning('setting does not exist')
            exit()

    def run_set(self, set_id: str):
        performed_set = self.get_performed_set(set_id)
        info(f'performed setting status: "{performed_set.status}"')

        if performed_set.status == 'running':
            performed_set.run_and_check()


def execute_setting(set_id: str):
    SettingExecution().run_set(set_id)
