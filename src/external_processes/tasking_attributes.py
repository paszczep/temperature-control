from src.internal_apis.models_data import TaskingValues, CheckValues, ControlValues
from src.internal_processes.controlling import (retrieve_tasking_controls,
                                                retrieve_tasking_control_temperature)
from src.internal_processes.controlling_new import ControllingTasking
from src.internal_processes.reading import ReadingTasking
from src.internal_processes.checking import CheckingTasking
from logging import info
from decimal import Decimal
from time import time
from typing import Union


class TaskingAttributes(TaskingValues):
    container_name: str
    checking: CheckingTasking
    controlling: ControllingTasking
    reading: ReadingTasking

    def __init__(self):
        self.checking = CheckingTasking(self.id)
        self.container_name = self.checking.container
        self.controlling = ControllingTasking(self.id)
        self.reading = ReadingTasking(self.id, self.container_name)

    def is_at_minimum(self) -> bool:
        return any(r <= self.t_min for r in self.reading.current_temperatures)

    def is_at_maximum(self) -> bool:
        return any(r >= self.t_max for r in self.reading.current_temperatures)

    def has_ever_reached_maximum(self) -> bool:
        return any(t >= self.t_max for t in self.reading.past_temperatures)

    def is_finished(self) -> bool:
        info(f'server time: {(now_time := int(time()))} '
             f'task start: {(task_start_time := self.start)} '
             f'task duration: {(task_duration := self.duration)}')
        if now_time > task_start_time + task_duration:
            return True

    def is_heating_up(self) -> bool:
        preheat_time = int((self.duration * 0.2) // 60)
        if self.has_started_ago(minutes=preheat_time):
            return True
        else:
            return False

    def may_require_cooling(self):
        cooling_time = int((self.duration * 0.4) // 60)
        if self.has_started_ago(minutes=cooling_time):
            return True
        else:
            return False

    def may_require_adjusting(self):
        cooling_time = int((self.duration * 0.5) // 60)
        if self.has_started_ago(minutes=cooling_time):
            return True
        else:
            return False
