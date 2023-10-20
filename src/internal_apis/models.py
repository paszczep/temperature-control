from src.internal_apis.database import (select_from_db, update_status_in_db, insert_one_object_into_db)
from dataclasses import dataclass, field
from random import choice
from typing import Union
from decimal import Decimal
from datetime import datetime
import pytz
import logging
import time
from uuid import uuid4

logger = logging.getLogger()


def is_younger_than(age_timestamp: int, minutes: int = 15) -> bool:
    return bool(age_timestamp > (time.time() - 60*minutes))


@dataclass
class DataObject:
    def get_log_info(self) -> str:
        object_dict_without_id = {key: value for key, value in self.__dict__.items() if key != 'id'}
        for key, value in object_dict_without_id.items():
            if 'time' in key and type(value) == int:
                object_dict_without_id[key] = datetime.strftime(
                    datetime.fromtimestamp(value), "%Y-%m-%d %H:%M")
        return str(object_dict_without_id)[1:-1].replace("'", "")


@dataclass
class Reading(DataObject):
    __tablename__ = 'read'
    id: str
    temperature: Union[str, Decimal]
    read_time: Union[str, int]
    db_time: int
    thermometer: str


def use_read(read_read: Reading) -> Reading:
    datetime_read = datetime.strptime(read_read.read_time, '%d/%m/%y %H:%M:%S')
    read_timezone = pytz.timezone('Europe/Berlin')
    datetime_local = read_timezone.localize(datetime_read)
    return Reading(
        id=read_read.id,
        temperature=Decimal(read_read.temperature[:-2]),
        read_time=int(datetime_local.timestamp()),
        db_time=read_read.db_time,
        thermometer=read_read.thermometer)


@dataclass(frozen=True)
class TaskRead:
    __tablename__ = 'task_reads'
    task_id: str
    read_id: str


@dataclass
class Thermometer:
    __tablename__ = 'thermometer'
    device_id: str
    device_group: str
    device_name: str


@dataclass(frozen=True)
class ContainerThermometer:
    __tablename__ = "container_thermometers"
    container_id: str
    thermometer_id: str


labels = ['Marcin', 'Klops', 'Marchew', 'Ziemia', 'Ojczyzna', 'Kazimierz', 'Marta', 'Fasola', 'Orzeszek', 'Rodzynek']


@dataclass
class Container:
    __tablename__ = 'Container'
    name: str
    label: str = field(default_factory=lambda: choice(labels))


@dataclass
class Control(DataObject):
    __tablename__ = 'control'
    id: str
    timestamp: int
    target_setpoint: str


@dataclass
class Check(DataObject):
    __tablename__ = 'container_check'
    id: str
    container: str
    timestamp: int
    logged: str
    received: str
    power: str
    read_setpoint: str


@dataclass(frozen=True)
class TaskControl:
    __tablename__ = "task_controls"
    task_id: str
    control_id: str


@dataclass(frozen=True)
class SetControl:
    __tablename__ = "set_controls"
    set_id: str
    control_id: str


@dataclass
class Tasking:
    __tablename__ = 'Task'
    id: str
    start: int
    duration: int
    t_start: int
    t_min: int
    t_max: int
    t_freeze: int
    status: str

    def is_not_done_yet(self) -> bool:
        logger.info(f'server time: {(now_time := int(time.time()))} '
                    f'task start: {(task_start_time := self.start)} '
                    f'task duration: {(task_duration := self.duration)}')
        if now_time < task_start_time + task_duration:
            return True


@dataclass(frozen=True)
class ContainerTask:
    __tablename__ = 'container_task'
    container_id: str
    task_id: str


@dataclass
class Setting:
    __tablename__ = 'temp_set'
    id: str
    status: str
    temperature: int
    timestamp: int


@dataclass(frozen=True)
class ContainerSet:
    __tablename__ = 'container_set'
    container_id: str
    set_id: str


data_objects = [Check,
                Control,
                Reading,
                Tasking,
                TaskRead,
                TaskControl,
                Setting,
                SetControl]

