from dataclasses import dataclass
from random import choice


@dataclass
class Read:
    __tablename__ = 'read'
    __relationship__ = "task_reads"
    id: int
    temperature: str
    read_time: str
    db_time: str
    thermometer: int
    task: int


@dataclass
class Thermometer:
    __tablename__ = 'thermometer'
    __relationship__ = "container_thermometers"
    device_id: int
    device_name: str


labels = ['Marcin', 'Klops', 'Kiełbasa', 'Zosia', 'Marchew', 'Ziemia', 'Ojczyzna']

@dataclass
class Container:
    __tablename__ = 'Container'
    name: str
    label: str = choice(labels)


@dataclass
class Ctrl:
    __tablename__ = 'Control'
    __relationship__ = "task_controls"
    id: int
    action: str
    timestamp: int
    logged: str
    received: str
    power: str
    target_setpoint: str
    read_setpoint: str
    task: int


@dataclass
class Task:
    __tablename__ = 'Task'
    __relationship__ = "container_task"
    id: int
    start: int
    duration: int
    t_start: int
    t_min: int
    t_max: int
    t_freeze: int
    status: str
