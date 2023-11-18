from src.external_apis.drive_control import ControlContainersDriver, DriverCheck
from typing import Union
from decimal import Decimal
from logging import info, warning


class DrivingAction:
    container_name: str
    temperature_setting: Union[int, str, Decimal]

    @staticmethod
    def parse_temperature_value(value: Union[int, str, Decimal]) -> Union[str, ValueError]:
        if value == '':
            raise ValueError
        elif isinstance(value, Decimal):
            value = str(value)
        if isinstance(value, int):
            value = f'{value}.0'
        elif isinstance(value, str) and value != '':
            if value[-2] == '.':
                pass
            elif '.' not in value:
                value = f'{value}.0'
        if not isinstance(value, str) and value[-2] == '.':
            warning(f'invalid setting value {value}')
            raise ValueError('Wrong temperature value')
        return value

    def __init__(self,
                 container_name: str,
                 temperature_setting: Union[int, str, Decimal]):
        info('driving initiating')
        self.container_name = container_name
        self.temperature_setting = self.parse_temperature_value(temperature_setting)

    def driver_check_and_introduce_setting(self) -> list[DriverCheck]:
        info(f'driving launching to set {self.temperature_setting} in {self.container_name}')
        return ControlContainersDriver().check_containers_and_set_temperature(
            container=self.container_name,
            temperature=self.temperature_setting)
