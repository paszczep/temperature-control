from dataclasses import dataclass, field
from random import choice
from typing import Union
from decimal import Decimal
from datetime import datetime
import pytz
from time import time


API_INTERVAL = 30


class Timestamped:
    timestamp: int
    INTERVAL = API_INTERVAL + 5

    def is_recent(self, minutes: int = INTERVAL + 5) -> bool:
        return bool(self.timestamp > (time() - 60 * minutes))


class DataObject:
    def get_log_info(self) -> str:
        skip_labels = ('id', 'container')
        log_object = {key: value for key, value in self.__dict__.items() if key not in skip_labels}
        for key, value in log_object.items():
            if 'time' in key and isinstance(value, int):
                log_object[key] = datetime.strftime(
                    datetime.fromtimestamp(value), "%Y-%m-%d %H:%M")
        return str(log_object)[1:-1].replace("'", "")


@dataclass
class ValuesReading(DataObject):
    __tablename__ = 'read'
    id: str
    temperature: Union[str, Decimal]
    read_time: Union[str, int]
    db_time: int
    thermometer: str

    def is_recent(self, minutes: int = Timestamped.INTERVAL) -> bool:
        return bool(self.read_time > (time() - 60 * minutes))


def use_read(read_read: ValuesReading) -> ValuesReading:
    datetime_read = datetime.strptime(read_read.read_time, '%d/%m/%y %H:%M:%S')
    read_timezone = pytz.timezone('Europe/Berlin')
    datetime_local = read_timezone.localize(datetime_read)
    return ValuesReading(
        id=read_read.id,
        temperature=Decimal(read_read.temperature[:-2]),
        read_time=int(datetime_local.timestamp()),
        db_time=read_read.db_time,
        thermometer=read_read.thermometer)


@dataclass(frozen=True)
class PairTaskRead:
    __tablename__ = 'task_reads'
    task_id: str
    read_id: str


@dataclass
class ThingThermometer:
    __tablename__ = 'thermometer'
    device_id: str
    device_group: str
    device_name: str


@dataclass(frozen=True)
class PairContainerThermometer:
    __tablename__ = "container_thermometers"
    container_id: str
    thermometer_id: str


labels = [
    'Marcin', 'Klops', 'Marchew', 'Ziemia', 'Ojczyzna', 'Kazimierz', 'Marta', 'Fasola', 'Orzeszek', 'Rodzynek',
    'Skrzypce', 'Kandelabr', 'Basia', 'Zofia', 'Tango', 'Rosja', 'Ryba', 'Manometr', 'Fajans', 'Inferencja',
    'Coulomb', 'Skrzypłocze', 'Gwint'
]


def choose_label() -> str:
    chosen_label = choice(labels)
    labels.remove(chosen_label)
    return chosen_label


@dataclass
class ThingContainer:
    __tablename__ = 'Container'
    name: str
    label: str = field(default_factory=lambda: choose_label())


@dataclass
class ValuesControl(DataObject, Timestamped):
    __tablename__ = 'control'
    id: str
    timestamp: int
    target_setpoint: str


@dataclass
class ValuesCheck(DataObject, Timestamped):
    __tablename__ = 'container_check'
    id: str
    container: str
    timestamp: int
    logged: str
    received: str
    power: str
    read_setpoint: Union[str, Decimal]


@dataclass(frozen=True)
class PairTaskControl:
    __tablename__ = "task_controls"
    task_id: str
    control_id: str


@dataclass(frozen=True)
class PairSetControl:
    __tablename__ = "set_controls"
    set_id: str
    control_id: str


@dataclass
class ValuesTasking:
    __tablename__ = 'Task'
    id: str
    start: int
    duration: int
    t_start: Union[int, Decimal]
    t_min: Union[int, Decimal]
    t_max: Union[int, Decimal]
    t_freeze: Union[int, Decimal]
    status: str

    def use_decimal_temperatures(self):
        self.t_start = Decimal(self.t_start)
        self.t_min = Decimal(self.t_min)
        self.t_max = Decimal(self.t_max)
        self.t_freeze = Decimal(self.t_freeze)


@dataclass(frozen=True)
class PairContainerTask:
    __tablename__ = 'container_task'
    container_id: str
    task_id: str


@dataclass
class ValuesSetting(Timestamped):
    __tablename__ = 'temp_set'
    id: str
    status: str
    temperature: Union[int, Decimal]
    timestamp: int


@dataclass(frozen=True)
class PairContainerSet:
    __tablename__ = 'container_set'
    container_id: str
    set_id: str


data_objects = [
    PairContainerThermometer,
    PairTaskRead,
    PairTaskControl,
    PairSetControl,
    PairContainerTask,
    PairContainerSet,
    ValuesCheck,
    ValuesControl,
    ValuesReading,
    ValuesTasking,
    ValuesSetting,
    ThingContainer,
    ThingThermometer,
]
