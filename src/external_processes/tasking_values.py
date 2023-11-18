from src.internal_apis.models import ValuesTasking
from src.internal_apis.database_query import select_from_db
from src.internal_processes.controlling import ControllingTasking
from src.internal_processes.reading import ReadingTasking
from src.internal_processes.checking import CheckingTasking
from logging import info
# from time import time
from typing import Union
from decimal import Decimal


class TaskingAttributes:
    task: ValuesTasking
    checking: CheckingTasking
    controlling: ControllingTasking
    reading: ReadingTasking
    COOLING_DELTA: int = 5

    @staticmethod
    def get_processed_task(task_id: str) -> ValuesTasking:
        info('fetching processed task')
        return [ValuesTasking(**s) for s in select_from_db(
            table_name=ValuesTasking.__tablename__, where_equals={'id': task_id})].pop()

    def __init__(self, task_id: str):
        self.task = self.get_processed_task(task_id)
        self.checking = CheckingTasking(self.task.id, self.task.start)
        self.controlling = ControllingTasking(self.task.id)
        self.reading = ReadingTasking(self.task.id, self.checking.container_name)
        self.task.use_decimal_temperatures()

    @staticmethod
    def _log_measures(settings: Union[list, list[str], list[Decimal]]) -> str:
        if not settings:
            return 'none found.'
        elif isinstance(settings[0], Decimal):
            return ', '.join(str(s) for s in settings)
        elif isinstance(settings[0], str):
            return ', '.join(settings)

    def is_at_minimum(self) -> bool:
        _t_min = [t for t in self.reading.current_temperatures if t <= self.task.t_min]
        info(f'values temperatures below minimum: {self._log_measures(_t_min)}')
        return any(_t_min)

    def is_at_maximum(self) -> bool:
        _t_max = [t for t in self.reading.current_temperatures if t >= self.task.t_max]
        info(f'values temperatures beyond maximum: {self._log_measures(_t_max)}')
        return any(_t_max)

    def has_before_reached_maximum(self) -> bool:
        past_t_max = [t for t in self.reading.past_temperatures if t >= self.task.t_max]
        info(f'values past temperatures beyond maximum: {self._log_measures(past_t_max)}')
        return any(past_t_max)

    def has_been_cooled_down(self) -> bool:
        info('values checking if cooling had been executed')
        settings = self.checking.settings
        info(f'values checked settings: {self._log_measures(settings)}')
        if (settings_len := len(settings)) >= 2:
            if any(
                    (settings[i] - settings[i + 1]) == self.COOLING_DELTA
                    for i in range(settings_len - 1)
            ):
                return True

    def has_been_cooled_down0(self) -> bool:
        _checks = self.checking.checks
        return False
