from src.external_apis.drive_control import CheckContainersDriver, DriverCheck
from src.internal_apis.database_query import (insert_multiple_objects_into_db, select_from_db)
from src.internal_apis.models import ValuesCheck, PairContainerTask, PairContainerSet
from uuid import uuid4
from decimal import Decimal
from typing import Union
from logging import info, warning


class _Checking:
    driver_checks: Union[None, list[DriverCheck]]
    created_checks: Union[None, list[ValuesCheck]]

    def _create_checks_from_driver(self):
        self.created_checks = [ValuesCheck(
            id=str(uuid4()),
            timestamp=c.database_time,
            container=c.name,
            logged=c.logged,
            received=c.received,
            power=c.power,
            read_setpoint=c.setpoint
        ) for c in self.driver_checks]

    def create_and_save_checks(self, driver_controls: Union[None, list[DriverCheck]] = None):
        info('check saving values')
        if driver_controls:
            self.driver_checks = driver_controls
        self._create_checks_from_driver()
        insert_multiple_objects_into_db(self.created_checks)

    def driver_check_containers(self):
        info('driver checking containers')
        self.driver_checks = CheckContainersDriver().read_values()
        self.create_and_save_checks()


def perform_check():
    _Checking().driver_check_containers()


class CheckingSetting(_Checking):
    set_id: str
    container: str

    def _get_set_container_name(self) -> str:
        info('check target container name')
        return [PairContainerSet(**c) for c in select_from_db(
            table_name=PairContainerSet.__tablename__, where_equals={'set_id': self.set_id})].pop().container_id

    def temperature_setting_verification(self) -> Union[Decimal, ValueError]:
        info('check working temperature setting value for comparison')
        _set_point = [
            c.setpoint for c in self.driver_checks
            if c.name == self.container].pop()
        if _set_point != '':
            _verified = Decimal(_set_point)
            info(f'check verified set point: {_verified}')
            return _verified
        else:
            warning('check no valid set point')
            raise ValueError

    def __init__(self, set_id: str):
        info('check initialize')
        self.set_id = set_id
        self.container = self._get_set_container_name()


class CheckingTasking(_Checking):
    _task_id: str
    _start: int
    container_name: str
    checks: list[ValuesCheck]
    settings: Union[None, list[Decimal]]
    recent: Union[None, Decimal]

    def _get_related_container_name(self) -> str:
        info('check relevant container name')
        return [PairContainerTask(**c) for c in select_from_db(
            table_name=PairContainerTask.__tablename__, where_equals={'task_id': self._task_id})].pop().container_id

    def _log_checks(self):
        info(f'check existing count: {len(self.checks)}')
        for check in self.checks:
            info(f'{check.get_log_info()}')

    def _retrieve_container_checks(self) -> Union[None, list[ValuesCheck]]:
        info('check retrieve existing values')
        select_checks = select_from_db(
            table_name=ValuesCheck.__tablename__,
            where_equals={'container': self.container_name},
            keys=True)
        info(f'check selected: {len(select_checks)}')
        if select_checks:
            checks = [ValuesCheck(**check) for check in select_checks]
            checks = [c for c in checks if c.timestamp >= self._start - 35 * 60]
            # descending order
            checks = sorted(checks, key=lambda c: c.timestamp, reverse=True)
            return checks
        else:
            info(f'check none existing')
            return None

    def __init__(self, task_id: str, task_start: int):
        self._task_id = task_id
        self._start = task_start
        self.container_name = self._get_related_container_name()
        self.checks = self._retrieve_container_checks()
        if self.checks:
            self._log_checks()
            self.settings = [Decimal(c.read_setpoint) for c in self.checks if c.read_setpoint != '']
            self.recent = self.settings[0] if self.settings else None
        else:
            self.settings = None
            self.recent = None
        info(f'check container: {self.container_name}')
        info(f'check recent point: {self.recent}')
