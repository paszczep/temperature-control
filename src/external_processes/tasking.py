from src.external_apis.drive import DriverExecuteError
from src.internal_processes.driving import driver_set_go_save_checks_and_control
from src.internal_processes.checking import (get_processed_task, error_task, end_task, check_containers,
                                             retrieve_recent_check_temperature, get_related_container_name)
from src.internal_processes.controlling import (retrieve_which_controls, retrieve_recent_control_temperature,
                                                InvalidSettingRetry, save_task_control)
from src.internal_processes.reading import measure_timely_temperature, retrieve_past_read_temperatures
import logging
from typing import Union
from decimal import Decimal
import time

logger = logging.getLogger()


def is_younger_than(age_timestamp: int, minutes: int = 15) -> bool:
    return bool(age_timestamp > (time.time() - 60 * minutes))


def task_process(task_id: str):
    logger.info('processing task')

    def set_temperature_if_necessary(
            temperature_setting: Union[int, Decimal],
            existing_check_temperature: Union[int, Decimal]):
        logger.info(f'considering {str(temperature_setting)}, provided {str(existing_check_temperature)}')
        if temperature_setting != existing_check_temperature:
            driver_set_go_save_checks_and_control(int(temperature_setting), task_id, task_container_name)
        else:
            logger.info('desired setting already active')
            save_task_control(existing_check_temperature, task_id)

    def set_temperature(temperature_setting: Union[int, Decimal]):
        logger.info(f'driver setting temperature {temperature_setting}')
        driver_set_go_save_checks_and_control(int(temperature_setting), task_id, task_container_name)

    def begin(check_setting: Union[Decimal, None] = None):
        logger.info('setting start temperature if necessary')
        if check_setting:
            set_temperature_if_necessary(
                temperature_setting=running_task.t_start,
                existing_check_temperature=check_setting)
        else:
            driver_set_go_save_checks_and_control(
                temperature_setting=running_task.t_start,
                task_id=task_id,
                task_container_name=task_container_name)

    def finish_process(check_temperature: Decimal):
        logger.info('finished task, setting t freeze')
        set_temperature_if_necessary(running_task.t_freeze, int(check_temperature))
        if check_temperature == running_task.t_freeze:
            logging.info('task finished, ending temperature set')
            end_task(running_task)

    def initiate_or_continue_task(existing_check_temperature: Decimal, measured_temperatures: list[Decimal]):

        def preheat():
            logger.info('preheating')
            logger.info('measuring maximum temperature')
            preheat_check = any(r >= running_task.t_max for r in measured_temperatures)
            if preheat_check:
                logger.info('preheat temperature reached')
                set_temperature_if_necessary(running_task.t_min - 5, existing_check_temperature)
            else:
                logger.info('preheat temperature yet unreached')

        def measure_and_decide(check_temperature: Decimal):
            logger.info('measure temperature and decide')
            minimum_check = any(r <= running_task.t_min for r in measured_temperatures)
            maximum_check = any(r >= running_task.t_max for r in measured_temperatures)
            if minimum_check:
                logger.info('minimum temperature reached')
                set_temperature(check_temperature + 1)
            elif maximum_check:
                logger.info('maximum temperature reached')
                set_temperature(check_temperature - 1)
            else:
                logger.info('temperature setting is ok')
                save_task_control(check_temperature, task_id)

        def control_process():
            what_control_ids = retrieve_which_controls(task_id)
            if not what_control_ids:
                if running_task.is_heating_up():
                    logging.info('no executed controls, task is young, beginning...')
                    set_temperature_if_necessary(running_task.t_start, existing_check_temperature)
                else:
                    logging.info('no executed controls, task is mature, measuring and deciding setting')
                    preheat()
            else:
                recent_control = retrieve_recent_control_temperature(what_control_ids)
                if recent_control:
                    logger.info(f'recent controlled temperature {str(recent_control)}')
                    if recent_control == running_task.t_start and running_task.is_heating_up():
                        logger.info('retry start temperature')
                        preheat()
                    elif recent_control != existing_check_temperature:
                        logger.info('retry previous setting')
                        driver_set_go_save_checks_and_control(int(recent_control), task_id, task_container_name)
                else:
                    logging.info('check if max has yet been reached')
                    all_past_temperatures = retrieve_past_read_temperatures(task_id)
                    if any(t > running_task.t_max for t in all_past_temperatures):
                        measure_and_decide(existing_check_temperature)

        control_process()

    def run_task():
        measured_temperatures = measure_timely_temperature(task_id)
        check_temperature = retrieve_recent_check_temperature(task_container_name)
        if not check_temperature:
            if is_younger_than(running_task.start, minutes=60):
                logger.info("IT'S A FRESH START")
                begin()
            else:
                logging.info('checking for setting benchmark')
                check_containers()
        elif not running_task.is_finished():
            logger.info("THERE EXISTS A BENCHMARK TO WORK WITH")
            initiate_or_continue_task(check_temperature, measured_temperatures)
        else:
            logger.info("finishing task process")
            finish_process(check_temperature)

    running_task = get_processed_task(task_id)
    task_container_name = get_related_container_name(task_id)

    if running_task.status == 'running':
        try:
            run_task()
        except (InvalidSettingRetry, DriverExecuteError) as ex:
            logging.warning(f'{ex}')
            error_task(bad_task=running_task)
