from src.external_apis.drive_control import DriverExecuteError
from src.internal_processes.controlling import InvalidSettingRetry
from src.external_processes.tasking_verify import TaskingVerify
from logging import info, warning
from time import time
# from typing import Union
# from decimal import Decimal


class TaskingProcess(TaskingVerify):

    def _log_time(self, now_time: int, relative_since_start: float):
        info(f'process time server: {now_time}')
        info(f'process time start:  {self.task.start}')
        info(f'process time done:   {int(relative_since_start * 100)} %')

    def task_staging(self):
        info('process staging')
        time_now = int(time())
        relative_since_start = (time_now - self.task.start) / self.task.duration
        self._log_time(time_now, relative_since_start)
        duration_stages = {
            (0, 0.125): self.task_beginning,
            (0.125, 0.25): self.task_consider_cooling,
            (0.25, 0.75): self.task_consider_adjusting,
            (0.75, 1.0): self.task_adjusting,
            (1.0, 1.25): self.task_finishing,
        }
        for stage, action in duration_stages.items():
            _open, _close = stage
            if _open < relative_since_start <= _close:
                action()
                break
        else:
            warning('process conclusion not reached beyond time threshold')
            self.drive_error_task()

    def task_process(self):
        info('process task begin')
        if self.controlling.settings:
            info('process benchmarks exist')
            self.verify_control_execution()
            self.verify_previous_setting()
        self.task_staging()


class TaskingRunning(TaskingProcess):

    def __init__(self, task_id: str):
        super().__init__(task_id)

    def run_task(self):
        info('process running task')

        if self.task.status == 'running':
            try:
                self.task_process()
            except (InvalidSettingRetry, DriverExecuteError) as ex:
                warning(f'task process exception {ex}')
                self.drive_error_task()


def perform_task(task_id: str):
    TaskingRunning(task_id=task_id).run_task()
