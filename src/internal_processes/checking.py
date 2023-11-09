from src.external_apis.drive import ContainerValuesDriver, DriveCtrl
from src.internal_apis.database_query import (insert_multiple_objects_into_db, select_from_db)
from src.internal_apis.models_data import CheckValues, ContainerTaskPair, ContainerSetPair
from uuid import uuid4
from decimal import Decimal
from typing import Union
from logging import info


class Checking:
    driver_ctrls: Union[None, list[DriveCtrl]]
    created_checks: Union[None, list[CheckValues]]

    def create_checks_from_ctrls(self):
        self.created_checks = [CheckValues(
            id=str(uuid4()),
            timestamp=c.database_time,
            container=c.name,
            logged=c.logged,
            received=c.received,
            power=c.power,
            read_setpoint=c.setpoint
        ) for c in self.driver_ctrls]

    def create_and_save_checks(self, driver_controls: Union[None, list[DriveCtrl]] = None):
        info('saving check values')
        if driver_controls:
            self.driver_ctrls = driver_controls
        self.create_checks_from_ctrls()
        insert_multiple_objects_into_db(self.created_checks)

    def driver_check_containers(self):
        info('driver checking containers')
        self.driver_ctrls = ContainerValuesDriver().read_values()
        self.create_and_save_checks()


def check_containers():
    Checking().driver_check_containers()


class CheckingSetting(Checking):
    set_id: str
    container: str

    def _get_set_container_name(self) -> str:
        info('fetching target container name')
        return [ContainerSetPair(**c) for c in select_from_db(
            table_name=ContainerSetPair.__tablename__, where_equals={'set_id': self.set_id})].pop().container_id

    def temperature_setting_verification(self) -> Decimal:
        info('fetching working temperature setting value for comparison')
        return [Decimal(c.setpoint) for c in self.driver_ctrls if c.name == self.container].pop()

    def __init__(self, set_id: str):
        self.set_id = set_id
        self.container = self._get_set_container_name()


class CheckingTasking(Checking):
    task_id: str
    container: str
    checks: list[CheckValues]
    recent_check: CheckValues

    def _get_related_container_name(self) -> str:
        info('fetching relevant container name')
        return [ContainerTaskPair(**c) for c in select_from_db(
            table_name=ContainerTaskPair.__tablename__, where_equals={'task_id': self.task_id})].pop().container_id

    def _retrieve_container_checks(self) -> Union[None, list[CheckValues]]:
        info('retrieving check temperature')
        select_checks = select_from_db(
            table_name=CheckValues.__tablename__,
            where_equals={'container': self.container},
            keys=True)
        if select_checks:
            checks = [(values := CheckValues(**check))
                      for check in select_checks
                      if values.is_younger_than(minutes=6 * 60)]
            checks = sorted(checks, key=lambda c: c.timestamp, reverse=True)
            info(f'selected checks {len(select_checks)}')
            for check in checks:
                info(f'existing checks {check.get_log_info()}')
            return checks
        else:
            info(f'no existing container checks')
            return None

    def _retrieve_recent_check_temperature(self) -> Union[Decimal, None]:
        info('retrieving check temperature')
        max_check_timestamp = max(c.timestamp for c in self.checks)
        existing_check = [check for check in self.checks if check.timestamp == max_check_timestamp].pop()
        info(f'existing check {existing_check.get_log_info()}')
        if existing_check.is_younger_than(minutes=60):
            info(f'existing check temperature {existing_check.read_setpoint}')
            return Decimal(existing_check.read_setpoint)

    def __init__(self, task_id: str):
        self.task_id = task_id
        self.container = self._get_related_container_name()
        self.checks = self._retrieve_container_checks()
        if self.checks:
            self.recent_check = self.checks[0]
