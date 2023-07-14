from dataclasses import dataclass
from random import choice


@dataclass
class Read:
    __tablename__ = 'read'
    id: int
    temperature: str
    read_time: str
    db_time: str
    thermometer: int


@dataclass
class TaskReads:
    __tablename__ = 'task_reads'
    task_id: int
    read_id: int



@dataclass
class Meter:
    __tablename__ = 'thermometer'
    device_id: int
    device_name: str

@dataclass
class ContainerMeter:
    __tablename__ = "container_thermometers"
    container_id: str
    thermometer_id: int



labels = ['Marcin', 'Klops', 'Kiełbasa', 'Zosia', 'Marchew', 'Ziemia', 'Ojczyzna']


@dataclass
class Container:
    __tablename__ = 'Container'
    name: str
    label: str = choice(labels)


@dataclass
class Ctrl:
    __tablename__ = 'Control'
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
class TaskCtrl:
    __tablename__ =  "task_controls"
    task_id: int
    control_id: int


@dataclass
class Task:
    __tablename__ = 'Task'
    id: int
    start: int
    duration: int
    t_start: int
    t_min: int
    t_max: int
    t_freeze: int
    status: str

    @staticmethod
    def columns():
        return {
            'id': int,
            'start': int,
            'duration': int,
            't_start': int,
            't_min': int,
            't_max': int,
            't_freeze': int,
            'status': str}

@dataclass
class ContainerTask:
    __tablename__ = 'container_task'
    container_id: str
    task_id: int
