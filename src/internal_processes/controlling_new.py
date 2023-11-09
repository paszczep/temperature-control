from src.external_apis.drive import DriveCtrl
from src.internal_apis.models_data import ControlValues, TaskControlPair, SettingTask, SetControlPair, ContainerSetPair, CheckValues, TaskingValues
from src.internal_apis.database_query import insert_one_object_into_db, select_from_db
from decimal import Decimal
from time import time
from uuid import uuid4
from typing import Union
from logging import info


class InvalidSettingRetry(Exception):
    def __init__(self, message="Retried setting to no effect"):
        self.message = message
        super().__init__(self.message)


class _Controlling:
    created_control: Union[None, ControlValues]

    def _str_temperature_value(self):
        if isinstance(self.created_control.target_setpoint, int):
            self.created_control.target_setpoint = f'{self.created_control.target_setpoint}.0'
        elif isinstance(self.created_control.target_setpoint, Decimal):
            self.created_control.target_setpoint = str(self.created_control.target_setpoint)

    def _create_and_save_control(self, temperature_setting: Union[int, str, Decimal]):
        info('saving control')
        self.created_control = ControlValues(
            id=str(uuid4()),
            timestamp=int(time()),
            target_setpoint=temperature_setting)
        self._str_temperature_value()
        insert_one_object_into_db(self.created_control)


class ControllingTasking(_Controlling):
    task_id: str
    controls: Union[None, list[ControlValues]]
    all_temperatures: Union[None, list[Decimal]]
    recent_temperature: Union[None, Decimal]

    def _retrieve_which_controls(self) -> Union[list[str], None]:
        info('retrieving task relevant controls ids')
        control_ids = select_from_db(table_name=TaskControlPair.__tablename__,
                                     columns=['control_id'],
                                     where_equals={'task_id': self.task_id},
                                     keys=False)
        return control_ids if control_ids else None

    def _retrieve_relevant_controls(self):
        info('retrieving task relevant controls')
        control_ids = self._retrieve_which_controls()
        if control_ids:
            self.controls = [
                ControlValues(**control) for control in
                select_from_db(ControlValues.__tablename__, where_in={'id': control_ids}, keys=True)]
            self.controls = sorted(self.controls, key=lambda c: c.timestamp, reverse=True)
            info(f'all task controls {len(self.controls)}')
            for control in self.controls:
                info(f'{control.get_log_info()}')
        else:
            info('no task controls executed')

    def _all_controlled_temperatures(self) -> list[Decimal]:
        return [Decimal(c.target_setpoint) for c in self.controls]

    def __init__(self, task_id: str):
        info('initiating task control')
        self.task_id = task_id
        self._retrieve_relevant_controls()
        self.all_temperatures = self._all_controlled_temperatures()
        self.recent_temperature = self.all_temperatures[0]

    def _create_task_control_pairing(self):
        info('pairing setting with created control')
        performed_control_relationship = TaskControlPair(
            control_id=self.created_control.id,
            task_id=self.task_id)
        insert_one_object_into_db(performed_control_relationship)

    def save_task_control(self, temperature_setting: Union[int, str, Decimal]):
        self._create_and_save_control(temperature_setting)
        self._create_task_control_pairing()


class ControllingSetting(_Controlling):
    set_id: str

    def _create_set_control_pairing(self):
        info('pairing setting with created control')
        performed_control_relationship = SetControlPair(
            control_id=self.created_control.id,
            set_id=self.set_id)
        insert_one_object_into_db(performed_control_relationship)

    def save_set_control(self, temperature_setting: Union[int, str, Decimal]):
        info('saving setting control')
        self._create_and_save_control(temperature_setting)
        self._create_set_control_pairing()

    def __init__(self, set_id: str):
        self.set_id = set_id
