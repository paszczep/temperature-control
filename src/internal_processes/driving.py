from src.external_apis.drive import ContainerSettingsDriver, DriveCtrl
from src.internal_processes.checking import Checking
from src.internal_processes.controlling import create_and_save_control, create_task_control_pairing
from typing import Union
from decimal import Decimal
from logging import info


def _parse_temperature_value(value: Union[int, str, Decimal]) -> str:
    if isinstance(value, int):
        value = f'{str(value)}.0'
    elif isinstance(value, Decimal):
        value = str(value)
    return value


class DrivingAction:
    process_id: str
    container_name: str
    temperature_setting: Union[int, str, Decimal]

    def __init__(self,
                 process_id: str,
                 container_name: str,
                 temperature_setting: Union[int, str, Decimal]):
        self.process_id = process_id
        self.container_name = container_name
        self.temperature_setting = _parse_temperature_value(temperature_setting)

    def driver_check_and_introduce_setting(self) -> list[DriveCtrl]:
        info(f'launching webdriver to set {self.temperature_setting} in {self.container_name}')
        return ContainerSettingsDriver().check_containers_and_set_temperature(
            container=self.container_name,
            temperature=self.temperature_setting)

    def driver_set_go_save_logs(self):
        info(f'initiating driver to set {str(self.temperature_setting)}')
        driver_checks = self.driver_check_and_introduce_setting()
        Checking().create_and_save_checks(driver_checks)
        performed_control = create_and_save_control(self.temperature_setting)
        create_task_control_pairing(performed_control, self.process_id)
