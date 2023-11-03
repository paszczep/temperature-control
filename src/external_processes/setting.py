from src.external_apis.drive import Ctrl
from src.internal_apis.database_query import select_from_db, update_status_in_db
from src.internal_apis.models_data import ContainerSetPair, Setting
from src.internal_processes.checking import create_and_save_checks
from src.internal_processes.controlling import create_and_save_control, create_set_control_pairing, get_setting_control
from src.internal_processes.driving import DrivingSetting
from logging import info, warning
from typing import Union
from decimal import Decimal


class SettingDriving(Setting):
    container_name: str
    temperature: Union[str, int]

    def get_set_container_name(self):
        info('fetching target container name')
        self.container_name = [ContainerSetPair(**c) for c in select_from_db(
            table_name=ContainerSetPair.__tablename__, where_equals={'set_id': self.id})].pop().container_id

    def parse_temperature_setting(self):
        if isinstance(self.temperature, int):
            self.temperature = f'{str(self.temperature)}.0'

    def execute_setting_driver(self) -> list[Ctrl]:
        info('running setting of temperature')
        self.get_set_container_name()
        self.parse_temperature_setting()
        return DrivingSetting(
            process_id=self.id,
            container_name=self.container_name,
            temperature_setting=self.temperature).driver_check_and_introduce_setting()


class SettingProcess(SettingDriving):

    def end_set(self):
        info('updating setting status to "ended"')
        self.status = 'ended'
        update_status_in_db(self)

    def run_and_check(self):
        container_controls = self.execute_setting_driver()
        create_and_save_checks(container_controls)
        performed_control = create_and_save_control(self.temperature)
        create_set_control_pairing(performed_control, self)
        setting_ctrl = get_setting_control(container_controls, self.container_name)
        info(f'settings - existing: {setting_ctrl.setpoint}, desired: {self.temperature}')
        if Decimal(setting_ctrl.setpoint) == Decimal(self.temperature):
            info('desired and provided settings are equal, ending process.')
            self.end_set()


class SettingExecution:
    @staticmethod
    def get_performed_set(set_id: str) -> SettingProcess:
        info('fetching setting parameters for execution')
        select_sets = select_from_db(table_name=Setting.__tablename__, where_equals={'id': set_id})
        if select_sets:
            return [SettingProcess(**s) for s in select_sets].pop()
        else:
            warning('setting does not exist')
            exit()

    def run_set(self, set_id: str):
        performed_set = self.get_performed_set(set_id)
        info(f'performed setting status: "{performed_set.status}"')

        if performed_set.status == 'running':
            performed_set.run_and_check()


def set_process(set_id: str):
    SettingExecution().run_set(set_id)
