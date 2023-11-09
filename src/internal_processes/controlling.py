from src.external_apis.drive import DriveCtrl
from src.internal_apis.models_data import ControlValues, TaskControlPair, SettingTask, SetControlPair, ContainerSetPair, CheckValues
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


def create_and_save_control(control_temperature: str) -> ControlValues:
    info('saving control')
    control = ControlValues(
        id=str(uuid4()),
        timestamp=int(time()),
        target_setpoint=control_temperature)
    insert_one_object_into_db(control)
    return control


def create_task_control_pairing(performed_task_control: ControlValues, related_task_id: str):
    info('pairing setting with created control')
    performed_control_relationship = TaskControlPair(
        control_id=performed_task_control.id,
        task_id=related_task_id)
    insert_one_object_into_db(performed_control_relationship)


def save_task_control(control_temperature: Union[int, Decimal], related_task_id: str):
    if isinstance(control_temperature, int):
        control_temperature = f'{control_temperature}.0'
    elif isinstance(control_temperature, Decimal):
        control_temperature = str(control_temperature)
    saved_control = create_and_save_control(control_temperature)
    create_task_control_pairing(saved_control, related_task_id)


def retrieve_which_controls(task_id: str) -> Union[list[str], None]:
    control_ids = select_from_db(table_name=TaskControlPair.__tablename__,
                                 columns=['control_id'],
                                 where_equals={'task_id': task_id},
                                 keys=False)
    return control_ids if control_ids else None


def create_set_control_pairing(performed_set_control: ControlValues, related_set: SettingTask):
    info('pairing setting with created control')
    performed_control_relationship = SetControlPair(
        control_id=performed_set_control.id,
        set_id=related_set.id)
    insert_one_object_into_db(performed_control_relationship)


def get_setting_control(all_controls: list[DriveCtrl], container_name: str) -> DriveCtrl:
    info('fetching working temperature setting value for comparison')
    return [c for c in all_controls if c.name == container_name].pop()


def retrieve_relevant_controls(control_ids: list) -> Union[None, list[ControlValues]]:
    all_task_controls = [
        ControlValues(**control) for control in
        select_from_db(ControlValues.__tablename__, where_in={'id': control_ids}, keys=True)]
    return all_task_controls


def retrieve_recent_control_temperature(control_ids: list) -> Union[Decimal, None]:
    all_task_controls = retrieve_relevant_controls(control_ids)
    info(f'all task controls {len(all_task_controls)}')
    for control in all_task_controls:
        info(f'{control.get_log_info()}')
    recent_timestamp = max(c.timestamp for c in all_task_controls)
    recent_control = [
        c.target_setpoint for c in all_task_controls
        if c.timestamp == recent_timestamp and c.is_younger_than()]
    if recent_control:
        recent_control = recent_control.pop()
        info(f'recent temperature control set point value {recent_control}')
        return Decimal(recent_control)
    else:
        return None


def retrieve_tasking_control_temperature(task_id: str) -> Union[Decimal, None]:
    control_ids = retrieve_which_controls(task_id=task_id)
    info('retrieving relevant control temperature')
    if control_ids:
        recent_temperature_control = retrieve_recent_control_temperature(control_ids)
        return recent_temperature_control
    else:
        return None


def retrieve_tasking_controls(task_id: str) -> Union[list[ControlValues], None]:
    control_ids = retrieve_which_controls(task_id=task_id)
    info('retrieving relevant controls')
    if control_ids:
        all_controls = retrieve_relevant_controls(control_ids)
        return all_controls
    else:
        return None
