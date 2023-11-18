from src.internal_apis.models import ValuesControl, PairTaskControl, PairSetControl
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
    created_control: Union[None, ValuesControl]

    def _str_temperature_value(self):
        if isinstance(self.created_control.target_setpoint, int):
            self.created_control.target_setpoint = f'{self.created_control.target_setpoint}.0'
        elif isinstance(self.created_control.target_setpoint, Decimal):
            self.created_control.target_setpoint = str(self.created_control.target_setpoint)

    def _create_and_save_control(self, temperature_setting: Union[int, str, Decimal]):
        info('control saving')
        self.created_control = ValuesControl(
            id=str(uuid4()),
            timestamp=int(time()),
            target_setpoint=temperature_setting)
        self._str_temperature_value()
        insert_one_object_into_db(self.created_control)


class ControllingTasking(_Controlling):
    _task_id: str
    _controls: Union[None, list[ValuesControl]]
    settings: Union[None, list[Decimal]]
    recent: Union[None, Decimal]

    def _retrieve_which_controls(self) -> Union[list[str], None]:
        info('control task relevant ids')
        control_ids = select_from_db(table_name=PairTaskControl.__tablename__,
                                     columns=['control_id'],
                                     where_equals={'task_id': self._task_id},
                                     keys=False)
        return control_ids if control_ids else None

    def _retrieve_relevant_controls(self) -> list[ValuesControl]:
        info('control task relevant retrieve')
        control_ids = self._retrieve_which_controls()
        if control_ids:
            controls = [
                ValuesControl(**control) for control in
                select_from_db(ValuesControl.__tablename__, where_in={'id': control_ids}, keys=True)]
            # descending order
            controls = sorted(controls, key=lambda c: c.timestamp, reverse=True)
            info(f'control total task count {len(controls)}')
            for control in controls:
                info(f'control {control.get_log_info()}')
            return controls
        else:
            info('control task none executed')

    def _all_controlled_temperatures(self) -> list[Decimal]:
        return [Decimal(c.target_setpoint) for c in self._controls]

    def __init__(self, task_id: str):
        info('control initiating')
        self._task_id = task_id
        self._controls = self._retrieve_relevant_controls()
        if self._controls:
            self.settings = self._all_controlled_temperatures()
            self.recent = self.settings[0]
        else:
            self.settings = None
            self.recent = None

    def _create_task_control_pairing(self):
        info('control pairing created')
        performed_control_relationship = PairTaskControl(
            control_id=self.created_control.id,
            task_id=self._task_id)
        insert_one_object_into_db(performed_control_relationship)

    def save_task_control(self, temperature_setting: Union[int, str, Decimal]):
        self._create_and_save_control(temperature_setting)
        self._create_task_control_pairing()


class ControllingSetting(_Controlling):
    set_id: str

    def _create_set_control_pairing(self):
        info('control pairing setting with created')
        performed_control_relationship = PairSetControl(
            control_id=self.created_control.id,
            set_id=self.set_id)
        insert_one_object_into_db(performed_control_relationship)

    def save_set_control(self, temperature_setting: Union[int, str, Decimal]):
        info('control saving setting')
        self._create_and_save_control(temperature_setting)
        self._create_set_control_pairing()

    def __init__(self, set_id: str):
        self.set_id = set_id
