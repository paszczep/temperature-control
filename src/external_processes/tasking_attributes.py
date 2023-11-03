from src.internal_apis.models_data import Tasking, Check, Control
from src.internal_processes.controlling import (retrieve_tasking_controls,
                                                retrieve_tasking_control_temperature)
from src.internal_processes.reading import measure_timely_temperature
from src.internal_processes.checking import (retrieve_recent_check_temperature,
                                             get_related_container_name, retrieve_relevant_checks)
from logging import info
from decimal import Decimal
from time import time
from typing import Union


class TaskingAttributes(Tasking):
    container_name: Union[None, str]
    check: Union[None, Decimal, int] = None
    control: Union[None, Decimal, int] = None
    measurements: Union[None, list[Decimal]] = None

    all_checks: Union[None, list[Check]] = None
    all_controls: Union[None, list[Control]] = None

    def fetch_attributes(self):
        self.container_name = get_related_container_name(self.id)
        self.check = retrieve_recent_check_temperature(self.container_name)
        self.control = retrieve_tasking_control_temperature(task_id=self.id)
        self.measurements = measure_timely_temperature(task_id=self.id)
        self.all_checks = retrieve_relevant_checks(self.container_name)
        self.all_controls = retrieve_tasking_controls(self.container_name)

    def is_at_minimum(self, measured_temperatures: list[Decimal]) -> bool:
        return any(r <= self.t_min for r in measured_temperatures)

    def is_at_maximum(self, measured_temperatures: list[Decimal]) -> bool:
        return any(r >= self.t_max for r in measured_temperatures)

    def has_ever_reached_maximum(self, all_past_temperatures: list[Decimal]) -> bool:
        return any(t >= self.t_max for t in all_past_temperatures)

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
