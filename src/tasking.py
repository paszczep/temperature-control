from .drive import ContainerSettingsDriver, Ctrl, DriverExecuteError
from .database import select_from_db, update_status_in_db, insert_one_object_into_db
from .api import Check, Control, ContainerTask, Tasking, TaskControl, use_read, Reading
from .reading import read_relevant_temperature
from .checking import create_and_save_checks, create_and_save_control, InvalidSettingRetry
import logging
from decimal import Decimal
import time
from typing import Union

logger = logging.getLogger()


def task_process(task_id: str):
    logger.info('processing task')

    def driver_set_go_save_checks_and_control(temperature_setting: int):
        def driver_check_and_introduce_setting(container_name: str, temp_setting: str) -> list[Ctrl]:
            logger.info(f'launching webdriver to set {temp_setting} in {container_name}')
            return ContainerSettingsDriver().check_containers_and_set_temperature(
                container=container_name,
                temperature=temp_setting)

        def create_task_control_pairing(performed_task_control: Control, related_task_id: str):
            logger.info('pairing setting with created control')
            performed_control_relationship = TaskControl(
                control_id=performed_task_control.id,
                task_id=related_task_id)
            insert_one_object_into_db(performed_control_relationship, TaskControl.__tablename__)

        read_relevant_temperature(task_id)
        logger.info(f'initiating driver to set {str(temperature_setting)}')
        driver_checks = driver_check_and_introduce_setting(
            container_name=task_container_name,
            temp_setting=(temperature_setting := f'{str(temperature_setting)}.0'))
        create_and_save_checks(driver_checks)
        performed_control = create_and_save_control(temperature_setting)
        create_task_control_pairing(performed_control, task_id)

    def retrieve_which_controls() -> list[str]:
        logger.info('establishing relevant controls')
        return select_from_db(table_name=TaskControl.__tablename__,
                              columns=['control_id'],
                              where_equals={'task_id': task_id},
                              keys=False)

    def retrieve_recent_control_temperature(control_ids: list) -> Decimal:
        logger.info('retrieving relevant controls')

        def check_for_control_errors(checked_controls: list[Control]):
            logger.info('checking for errors')
            points = [c.target_setpoint for c in checked_controls]
            logger.info(f'existing executed controls: {str(points)[1:-1]}')
            if len(points) >= 4:
                if points[-1] == points[-2] == points[-3] == points[-4]:
                    raise InvalidSettingRetry

        all_task_controls = [
            Control(**control) for control in
            select_from_db(Control.__tablename__, where_in={'id': control_ids}, keys=True)]
        logger.info(f'all task controls {len(all_task_controls)}')
        for cont in all_task_controls:
            logger.info(f'{cont.get_log_info()}')

        check_for_control_errors(all_task_controls)
        recent_timestamp = max(c.timestamp for c in all_task_controls)
        recent_temperature_control = [
            c.target_setpoint for c in all_task_controls
            if c.timestamp == recent_timestamp and is_younger_than(c.timestamp)].pop()

        logger.info(f'recent temperature control set point value {recent_temperature_control}')

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
        logger.info(f'selected checks {len(select_checks)}')
        if select_checks:
            all_checks = [Check(**check) for check in select_checks]
            max_check_timestamp = max(c.timestamp for c in all_checks)
            existing_check = [check for check in all_checks if check.timestamp == max_check_timestamp].pop()
            logger.info(f'existing check {existing_check.get_log_info()}')
            if is_younger_than(existing_check.timestamp, minutes=20):
                logger.info(f'existing check temperature {existing_check.read_setpoint}')
                return Decimal(existing_check.read_setpoint)

    def begin():
        logger.info('beginning task, setting start temperature')
        return driver_set_go_save_checks_and_control(temperature_setting=running_task.t_start)

    def measure_all_temperature() -> list[Reading]:
        logger.info('read all temperature')
        read_all = [use_read(r) for r in read_relevant_temperature(task_id)]
        logger.info(f'all thermometer reads {len(read_all)}:')
        for log_all_read in read_all:
            logger.info(f'{log_all_read.get_log_info()}')
        return read_all

    def measure_timely_temperature() -> list[Decimal]:
        logger.info('measuring temperature')
        read_all = measure_all_temperature()
        read_valid = [r.temperature for r in read_all if is_younger_than(r.read_time)]
        logger.info(f'valid thermometer reads {len(read_valid)}')
        for log_read in read_valid:
            logger.info(f'valid temperature read {log_read}')
        return read_valid

    def initiate_or_continue_task(existing_check_temperature: Decimal):

        def set_temperature_if_necessary(temperature_setting: int):
            logger.info(f'considering {str(temperature_setting)}, provided {str(existing_check_temperature)}')
            if temperature_setting != existing_check_temperature:
                driver_set_go_save_checks_and_control(temperature_setting)
            else:
                logger.info('desired setting already active')

        def preheat():
            logger.info('preheating')
            if existing_check_temperature != running_task.t_start:
                logger.info('existing checked setting is not equal to T start')
                begin()
            else:
                logger.info('measuring maximum temperature')
                measured_maximum_temperatures = measure_timely_temperature()
                preheat_check = any(r >= running_task.t_max for r in measured_maximum_temperatures)
                if preheat_check:
                    logger.info('preheat temperature reached')
                    set_temperature_if_necessary(running_task.t_min)
                else:
                    logger.info('preheat temperature yet unreached')

        def measure_and_decide():
            logger.info('measure temperature and decide')
            measured_temperatures = measure_timely_temperature()
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

        what_control_ids = retrieve_which_controls()
        if not what_control_ids:
            logging.info('no executed controls, beginning task')
            begin()
        else:
            control_temperature = retrieve_recent_control_temperature(what_control_ids)
            logger.info(f'recent controlled temperature {str(control_temperature)}')
            if control_temperature == running_task.t_start and is_younger_than(running_task.start, minutes=60):
                logger.info('retry start temperature')
                preheat()
            elif control_temperature != existing_check_temperature:
                logger.info('retry previous setting')
                driver_set_go_save_checks_and_control(int(control_temperature))
            else:
                measure_and_decide()

    def error_task(bad_task: Tasking):
        logger.info('task error')
        bad_task.status = 'error'
        update_status_in_db(bad_task)

    def deal_with_time() -> bool:
        logger.info(f'server time: {(now_time := int(time.time()))} '
                    f'task start: {(task_start_time := running_task.start)} '
                    f'task duration: {(task_duration := running_task.duration)}')
        if now_time < task_start_time + task_duration:
            return True

    def run_task():
        if deal_with_time():
            check_temperature = retrieve_check_temperature(task_container_name)
            if not check_temperature:
                logger.info("IT'S A FRESH START")
                begin()
            elif check_temperature:
                logger.info("THERE EXISTS A BENCHMARK TO WORK WITH")
                initiate_or_continue_task(check_temperature)
        else:
            logger.info('finished task, setting t freeze')
            driver_set_go_save_checks_and_control(running_task.t_freeze)

    def get_processed_task() -> Tasking:
        logger.info('fetching processed task')
        return [Tasking(**s) for s in select_from_db(
            table_name=Tasking.__tablename__, where_equals={'id': task_id})].pop()

    running_task = get_processed_task()
    task_container_name = get_related_container_name()

    if running_task.status == 'running':
        try:
            run_task()
        except (InvalidSettingRetry, DriverExecuteError) as ex:
            logging.warning(f'{ex}')
            error_task(running_task)
