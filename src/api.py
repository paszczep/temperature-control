from dataclasses import dataclass, field
from random import choice
from typing import Union
from decimal import Decimal
from datetime import datetime
import pytz
from .database import select_from_db
import logging


@dataclass
class Reading:
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




@dataclass
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


@dataclass
class ContainerThermometer:
    __tablename__ = "container_thermometers"
    container_id: str
    thermometer_id: str


labels = ['Marcin', 'Klops', 'Marchew', 'Ziemia', 'Ojczyzna', 'Kazimierz', 'Marta', 'Fasola']


@dataclass
class Container:
    __tablename__ = 'Container'
    name: str
    label: str = field(default_factory=lambda: choice(labels))


@dataclass
class Control:
    __tablename__ = 'control'
    id: str
    timestamp: int
    target_setpoint: str


@dataclass
class Check:
    __tablename__ = 'container_check'
    id: str
    container: str
    timestamp: int
    logged: str
    received: str
    power: str
    read_setpoint: str


@dataclass
class TaskControl:
    __tablename__ = "task_controls"
    task_id: str
    control_id: str


@dataclass
class SetControl:
    __tablename__ = "set_controls"
    set_id: str
    control_id: str


@dataclass
class Task:
    __tablename__ = 'Task'
    id: str
    start: int
    duration: int
    t_start: int
    t_min: int
    t_max: int
    t_freeze: int
    status: str


@dataclass
class ContainerTask:
    __tablename__ = 'container_task'
    container_id: str
    task_id: str


def get_related_container(task_id: str) -> ContainerTask:
    logging.info('fetching processed container')
    return [ContainerTask(**c) for c in select_from_db(
        table_name=ContainerTask.__tablename__, where_equals={'task_id': task_id})].pop()


@dataclass
class Set:
    __tablename__ = 'temp_set'
    id: str
    status: str
    temperature: int
    timestamp: int


@dataclass
class ContainerSet:
    __tablename__ = 'container_set'
    container_id: str
    set_id: str


data_objects = [ContainerTask, ContainerSet, Check, Control,
                Reading,
                Task,
                TaskRead,
                TaskControl,
                Set,
                SetControl]

