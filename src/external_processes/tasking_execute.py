from src.internal_apis.database_query import update_status_in_db
from src.internal_processes.driving import DrivingAction
from src.internal_processes.controlling import (save_task_control)
from src.external_processes.tasking_attributes import TaskingAttributes
from logging import info
from decimal import Decimal
from typing import Union


class TaskingExecution(TaskingAttributes):
    intended_setting: Union[int, Decimal]

    def set_temperature(self):
        info(f'task driver setting '
             f'temperature: {self.intended_setting}'
             f'in container: {self.container_name}')
        DrivingAction(
            process_id=self.id,
            container_name=self.container_name,
            temperature_setting=self.intended_setting).driver_set_go_save_logs()

    def set_temperature_if_necessary(self):
        info(f'task considering {str(self.intended_setting)}, provided {str(self.check)}')
        if self.control != self.check:
            self.intended_setting = self.control
            self.set_temperature()
        else:
            info('desired setting already active')
            save_task_control(self.check, self.id)

    def error_task(self):
        info('task error')
        self.status = 'error'
        update_status_in_db(self)

    def end_task(self):
        info('ending task')
        self.status = 'ended'
        update_status_in_db(self)
