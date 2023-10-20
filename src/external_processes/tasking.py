from src.external_apis.drive import DriverExecuteError
from src.internal_processes.driving import driver_set_go_save_checks_and_control
from src.internal_processes.checking import (get_processed_task, error_task,
                                             retrieve_recent_check_temperature, get_related_container_name)
from src.internal_processes.controlling import (retrieve_which_controls, retrieve_recent_control_temperature,
                                                InvalidSettingRetry)
from src.internal_processes.reading import measure_timely_temperature
import logging
from decimal import Decimal
import time

logger = logging.getLogger()


def is_younger_than(age_timestamp: int, minutes: int = 15) -> bool:
    return bool(age_timestamp > (time.time() - 60 * minutes))


def task_process(task_id: str):
    logger.info('processing task')

    def begin():
        logger.info('beginning task, setting start temperature')
        return driver_set_go_save_checks_and_control(
            temperature_setting=running_task.t_start, task_id=task_id, task_container_name=task_container_name)

    def initiate_or_continue_task(existing_check_temperature: Decimal):

        def set_temperature_if_necessary(temperature_setting: int):
            logger.info(f'considering {str(temperature_setting)}, provided {str(existing_check_temperature)}')
            if temperature_setting != existing_check_temperature:
                driver_set_go_save_checks_and_control(temperature_setting, task_id, task_container_name)
            else:
                logger.info('desired setting already active')

        def preheat():
            logger.info('preheating')
            if existing_check_temperature != running_task.t_start:
                logger.info('existing checked setting is not equal to T start')
                begin()
            else:
                logger.info('measuring maximum temperature')
                measured_maximum_temperatures = measure_timely_temperature(task_id)
                preheat_check = any(r >= running_task.t_max for r in measured_maximum_temperatures)
                if preheat_check:
                    logger.info('preheat temperature reached')
                    set_temperature_if_necessary(running_task.t_min)
                else:
                    logger.info('preheat temperature yet unreached')

        def measure_and_decide():
            logger.info('measure temperature and decide')
            measured_temperatures = measure_timely_temperature(task_id)
            minimum_check = any(r <= running_task.t_min for r in measured_temperatures)
            maximum_check = any(r >= running_task.t_max for r in measured_temperatures)
            if minimum_check:
                logger.info('minimum temperature reached')
                set_temperature_if_necessary(int(control_temperature) + 1)
            elif maximum_check:
                logger.info('maximum temperature reached')
                set_temperature_if_necessary(int(control_temperature) - 1)
            else:
                logger.info('temperature setting is ok')

        what_control_ids = retrieve_which_controls(task_id)
        if not what_control_ids:
            logging.info('no executed controls, beginning task')
            begin()
        else:
            control_temperature = retrieve_recent_control_temperature(what_control_ids)
            logger.info(f'recent controlled temperature {str(control_temperature)}')
            if control_temperature == running_task.t_start and is_younger_than(running_task.start, minutes=20):
                logger.info('retry start temperature')
                preheat()
            elif control_temperature != existing_check_temperature:
                logger.info('retry previous setting')
                driver_set_go_save_checks_and_control(int(control_temperature), task_id, task_container_name)
            else:
                measure_and_decide()

    def run_task():
        if running_task.is_not_done_yet():
            check_temperature = retrieve_recent_check_temperature(task_container_name)
            if not check_temperature:
                logger.info("IT'S A FRESH START")
                begin()
            elif check_temperature:
                logger.info("THERE EXISTS A BENCHMARK TO WORK WITH")
                initiate_or_continue_task(check_temperature)
        else:
            logger.info('finished task, setting t freeze')
            driver_set_go_save_checks_and_control(running_task.t_freeze, task_id, task_container_name)

    running_task = get_processed_task(task_id)
    task_container_name = get_related_container_name(task_id)

    if running_task.status == 'running':
        try:
            run_task()
        except (InvalidSettingRetry, DriverExecuteError) as ex:
            logging.warning(f'{ex}')
            error_task(bad_task=running_task)
