from dataclasses import dataclass, field
from random import choice


@dataclass
class Read:
    __tablename__ = 'read'
    id: str
    temperature: str
    read_time: str
    db_time: int
    thermometer: str


@dataclass
class TaskReads:
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
    __tablename__ = 'Control'
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
