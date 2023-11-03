from src.external_apis.drive import DriverExecuteError
from src.internal_processes.controlling import InvalidSettingRetry
from src.internal_apis.models_data import Tasking
from src.internal_apis.database_query import select_from_db
from src.internal_processes.checking import check_containers
from src.external_processes.tasking_control import TaskingControlling
from logging import info, warning
# from decimal import Decimal
# from time import time
# from typing import Union


class TaskingProcessing(TaskingControlling):

    def task_process(self):
        self.fetch_attributes()
        if not self.check:
            if not self.has_started_ago(minutes=60):
                info("task process just started")
                self.beginning()
            elif self.is_finished():
                info("task process is finished")
                self.finishing()
            else:
                info('task process setting benchmark required, checking')
                check_containers()
        elif not self.is_finished():
            info("task process benchmark exists")
            self.control_process()
        else:
            info("finishing task process")
            self.finishing()


class TaskingRunning(TaskingProcessing):
    task_id: str

    def __init__(self, task_id: str):
        self.task_id = task_id

    def get_processed_task(self) -> TaskingProcessing:
        info('fetching processed task')
        return [TaskingProcessing(**s) for s in select_from_db(
            table_name=Tasking.__tablename__, where_equals={'id': self.task_id})].pop()

    def run_task(self):
        info('running task process')
        running_task = self.get_processed_task()

        if running_task.status == 'running':
            try:
                running_task.task_process()
            except (InvalidSettingRetry, DriverExecuteError) as ex:
                warning(f'task process exception {ex}')
                running_task.error_task()


def task_process(task_id: str):
    TaskingRunning(task_id=task_id).run_task()
