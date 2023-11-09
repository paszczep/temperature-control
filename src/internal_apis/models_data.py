from dataclasses import dataclass, field
from random import choice
from typing import Union
from decimal import Decimal
from datetime import datetime
import pytz
from time import time

CHECK_MINUTES_INTERVAL = 15


def _string_temperature(value: Union[int, str, Decimal]) -> str:
    if isinstance(value, int):
        value = f'{value}.0'
    elif isinstance(value, Decimal):
        value = str(value)
    elif isinstance(value, str) and value[-2] == '.':
        pass
    else:
        raise ValueError('Wrong temperature value')
    return value


class Timestamped:
    timestamp: int

    def is_younger_than(self, minutes: int = CHECK_MINUTES_INTERVAL) -> bool:
        return bool(self.timestamp > (time() - 60*minutes))


class DataObject:
    def get_log_info(self) -> str:
        object_dict_without_id = {key: value for key, value in self.__dict__.items() if key != 'id'}
        for key, value in object_dict_without_id.items():
            if 'time' in key and isinstance(value, int):
                object_dict_without_id[key] = datetime.strftime(
                    datetime.fromtimestamp(value), "%Y-%m-%d %H:%M")
        return str(object_dict_without_id)[1:-1].replace("'", "")


@dataclass
class ReadingValues(DataObject):
    __tablename__ = 'read'
    id: str
    temperature: Union[str, Decimal]
    read_time: Union[str, int]
    db_time: int
    thermometer: str

    def is_younger_than(self, minutes: int = CHECK_MINUTES_INTERVAL) -> bool:
        return bool(self.read_time > (time() - 60*minutes))


def use_read(read_read: ReadingValues) -> ReadingValues:
    datetime_read = datetime.strptime(read_read.read_time, '%d/%m/%y %H:%M:%S')
    read_timezone = pytz.timezone('Europe/Berlin')
    datetime_local = read_timezone.localize(datetime_read)
    return ReadingValues(
        id=read_read.id,
        temperature=Decimal(read_read.temperature[:-2]),
        read_time=int(datetime_local.timestamp()),
        db_time=read_read.db_time,
        thermometer=read_read.thermometer)


@dataclass(frozen=True)
class TaskReadPair:
    __tablename__ = 'task_reads'
    task_id: str
    read_id: str


@dataclass
class ThermometerThing:
    __tablename__ = 'thermometer'
    device_id: str
    device_group: str
    device_name: str


@dataclass(frozen=True)
class ContainerThermometerPair:
    __tablename__ = "container_thermometers"
    container_id: str
    thermometer_id: str


labels = [
    'Marcin', 'Klops', 'Marchew', 'Ziemia', 'Ojczyzna', 'Kazimierz', 'Marta', 'Fasola', 'Orzeszek', 'Rodzynek',
    'Skrzypce', 'Kandelabr', 'Basia', 'Zofia', 'Tango', 'Rosja', 'Ryba'
          ]


def choose_label() -> str:
    chosen_label = choice(labels)
    labels.remove(chosen_label)
    return chosen_label


@dataclass
class ContainerThing:
    __tablename__ = 'Container'
    name: str
    label: str = field(default_factory=lambda: choose_label())


@dataclass
class ControlValues(DataObject, Timestamped):
    __tablename__ = 'control'
    id: str
    timestamp: int
    target_setpoint: str


@dataclass
class CheckValues(DataObject, Timestamped):
    __tablename__ = 'container_check'
    id: str
    container: str
    timestamp: int
    logged: str
    received: str
    power: str
    read_setpoint: str


@dataclass(frozen=True)
class TaskControlPair:
    __tablename__ = "task_controls"
    task_id: str
    control_id: str


@dataclass(frozen=True)
class SetControlPair:
    __tablename__ = "set_controls"
    set_id: str
    control_id: str


@dataclass
class TaskingValues:
    __tablename__ = 'Task'
    id: str
    start: int
    duration: int
    t_start: int
    t_min: int
    t_max: int
    t_freeze: int
    status: str

    def has_started_ago(self, minutes: int = CHECK_MINUTES_INTERVAL) -> bool:
        return bool(self.start > (time() - 60*minutes))


@dataclass(frozen=True)
class ContainerTaskPair:
    __tablename__ = 'container_task'
    container_id: str
    task_id: str


@dataclass
class SettingTask(Timestamped):
    __tablename__ = 'temp_set'
    id: str
    status: str
    temperature: int
    timestamp: int


@dataclass(frozen=True)
class ContainerSetPair:
    __tablename__ = 'container_set'
    container_id: str
    set_id: str


data_objects = [ContainerThing,
                ThermometerThing,
                ContainerThermometerPair,
                CheckValues,
                ControlValues,
                ReadingValues,
                TaskingValues,
                TaskReadPair,
                TaskControlPair,
                SettingTask,
                SetControlPair]
