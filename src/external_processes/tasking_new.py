from src.external_apis.drive import DriverExecuteError
from src.internal_processes.driving import driver_set_go_save_checks_and_control
from src.internal_processes.checking import (get_processed_task, error_task, end_task, check_containers,
                                             retrieve_recent_check_temperature, get_related_container_name)
from src.internal_processes.controlling import (retrieve_which_controls, retrieve_recent_control_temperature,
                                                InvalidSettingRetry)
from src.internal_processes.reading import measure_timely_temperature, retrieve_past_read_temperatures
import logging
from typing import Union
from decimal import Decimal
import time


def run_task(task_id: str):
    running_task = get_processed_task(task_id)
    if running_task.status == 'start':
        # set start temperature
        # verify (t check) = (t start)
        # set status to 'heat'
        pass

    elif running_task.status == 'heat':
        # check for max temperature
        # if reached set (t min - 5)
        # check setting
        # set status to
        pass

    elif running_task.status == 'cool':
        pass

    elif running_task.status == 'freeze':
        pass

