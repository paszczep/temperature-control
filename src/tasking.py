from .drive import ContainerSettingsDriver, Ctrl, DriverExecuteError
from .database import select_from_db, update_status_in_db, insert_one_object_into_db
from .api import Check, Control, ContainerTask, Task, TaskControl, use_read
from .reading import read_relevant_temperature
from .checking import create_and_save_checks, create_and_save_control, InvalidSettingRetry
import logging
from decimal import Decimal
import time
from typing import Union

logger = logging.getLogger()


def task_process(task_id: str):
    logger.info('processing task')

    def create_task_control_pairing(performed_task_control: Control, related_task_id: str):
        logger.info('pairing setting with created control')
        performed_control_relationship = TaskControl(
            control_id=performed_task_control.id,
            task_id=related_task_id)
        insert_one_object_into_db(performed_control_relationship, TaskControl.__tablename__)

    def driver_check_and_introduce_setting(container_name: str, temp_setting: str) -> list[Ctrl]:
        logger.info(f'launching webdriver to set {temp_setting} in {container_name}')
        return ContainerSettingsDriver().check_containers_and_set_temperature(
            container=container_name,
            temperature=temp_setting)

    def driver_set_go_save_checks_and_control(temperature_setting: int):
        read_relevant_temperature(task_id)
        logger.info(f'initiating driver to set {str(temperature_setting)}')
        driver_checks = driver_check_and_introduce_setting(
            container_name=task_container_name,
            temp_setting=(temperature_setting := f'{str(temperature_setting)}.0'))
        create_and_save_checks(driver_checks)
        performed_control = create_and_save_control(temperature_setting)
        create_task_control_pairing(performed_control, task_id)

    def get_processed_task() -> Task:
        logger.info('fetching processed task')
        return [Task(**s) for s in select_from_db(
            table_name=Task.__tablename__, where_equals={'id': task_id})].pop()

    def retrieve_which_controls() -> list[str]:
        logger.info('establishing relevant controls')
        return select_from_db(table_name=TaskControl.__tablename__,
                              columns=['control_id'],
                              where_equals={'task_id': task_id},
                              keys=False)

    def check_for_control_errors(checked_controls: list[Control]):
        logger.info('checking for errors')
        points = [c.target_setpoint for c in checked_controls]
        if len(points) >= 3:
            for i in range(len(points)):
                if points[i] == points[i + 1] == points[i + 2]:
                    raise InvalidSettingRetry

    def retrieve_recent_control_temperature(control_ids: list) -> Decimal:
        logger.info('retrieving relevant controls')
        all_task_controls = [
            Control(**control) for control in
            select_from_db(Control.__tablename__, where_in={'id': control_ids}, keys=True)]
        check_for_control_errors(all_task_controls)
        recent_timestamp = max(c.timestamp for c in all_task_controls)
        recent_temperature_control = [
            c.target_setpoint for c in all_task_controls
            if c.timestamp == recent_timestamp and is_younger_than(c.timestamp)].pop()
        return Decimal(recent_temperature_control)

    def get_related_container_name() -> str:
        logger.info('fetching processed container')
        return [ContainerTask(**c) for c in select_from_db(
            table_name=ContainerTask.__tablename__, where_equals={'task_id': task_id})].pop().container_id

    def is_younger_than(age_timestamp: int, minutes: int = 15) -> bool:
        return bool(age_timestamp > (time.time() - 60*minutes))

    def retrieve_check_temperature(checked_container_id: str) -> Union[Decimal, None]:
        logger.info('retrieving check temperature')
        select_checks = select_from_db(
                            table_name=Check.__tablename__,
                            where_equals={'container': checked_container_id},
                            keys=True)
        if select_checks:
            existing_check = [Check(**check) for check in select_checks].pop()
            if is_younger_than(existing_check.timestamp):
                return Decimal(existing_check.read_setpoint)

    def begin_task():
        logger.info('setting start temperature')
        return driver_set_go_save_checks_and_control(temperature_setting=running_task.t_start)

    def measure_temperature() -> list[Decimal]:
        logger.info('measuring temperature')
        read_all = [use_read(r) for r in read_relevant_temperature(task_id)]
        read_valid = [Decimal(r.temperature[:-2]) for r in read_all if is_younger_than(r.read_time)]
        return read_valid

    def initiate_or_continue(existing_check_temperature: Decimal):
        def preheat():
            logger.info('preheating')
            if existing_check_temperature != running_task.t_start:
                begin_task()
            else:
                measured_maximum_temperatures = measure_temperature()
                preheat_check = any(r >= running_task.t_max for r in measured_maximum_temperatures)
                if preheat_check:
                    driver_set_go_save_checks_and_control(running_task.t_min)

        def measure_and_decide():
            measured_temperatures = measure_temperature()
            minimum_check = any(r <= running_task.t_min for r in measured_temperatures)
            if minimum_check:
                driver_set_go_save_checks_and_control(int(control_temperature) + 1)
            maximum_check = any(r >= running_task.t_max for r in measured_temperatures)
            if maximum_check:
                driver_set_go_save_checks_and_control(int(control_temperature) - 1)

        what_control_ids = retrieve_which_controls()
        if not what_control_ids:
            logging.info('beginning task')
            begin_task()
        else:
            control_temperature = retrieve_recent_control_temperature(what_control_ids)
            if control_temperature == running_task.t_start:
                logging.info('retry t start')
                preheat()
            elif control_temperature != existing_check_temperature:
                driver_set_go_save_checks_and_control(int(control_temperature))
            else:
                measure_and_decide()

    def error_task(bad_task: Task):
        logger.info('task error')
        bad_task.status = 'error'
        update_status_in_db(bad_task)

    def run_task():
        check_temperature = retrieve_check_temperature(task_container_name)
        if not check_temperature and is_younger_than(running_task.start):
            begin_task()
        elif check_temperature:
            initiate_or_continue(check_temperature)

    running_task = get_processed_task()
    task_container_name = get_related_container_name()

    if running_task.status == 'running':
        try:
            run_task()
        except (InvalidSettingRetry, DriverExecuteError) as ex:
            logging.warning(f'{ex}')
            error_task(running_task)
