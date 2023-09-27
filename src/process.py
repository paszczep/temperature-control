from .drive import ContainerValuesDriver, ContainerSettingsDriver, Ctrl, ExecuteButtonError
from .measure import read_all_thermometers, Measure
from .database import insert_multiple_objects_into_db, clear_table, select_from_db, update_status_in_db, \
    insert_one_object_into_db
from .api import Container, Check, Control, ContainerSet, ContainerThermometer, ContainerTask, Thermometer, Reading, \
    TaskRead, Task, Set, SetControl, TaskControl, data_objects, use_read
from uuid import uuid4
import logging
from decimal import Decimal
import time
from typing import Union
import sys
#
# logging.basicConfig(
#     stream=sys.stdout,
#     level=logging.DEBUG,
#     format='%(asctime)s: %(message)s'
# )

logger = logging.getLogger()


def initialize_database():
    def clear_data_tables():
        logger.info('clearing data tables')
        for cleared_object in data_objects:
            clear_table(cleared_object.__tablename__)

    def insert_containers():
        logger.info('inserting containers')
        container_values_read = ContainerValuesDriver().read_values()
        containers = [Container(name=container.name) for container in container_values_read]
        clear_table(container_table := Container.__tablename__)
        insert_multiple_objects_into_db(containers, container_table)

        control_data = [
            Check(
                id=str(uuid4()),
                timestamp=c.database_time,
                container=c.name,
                logged=c.logged,
                received=c.received,
                power=c.power,
                read_setpoint=c.setpoint
            )
            for c in container_values_read]
        insert_multiple_objects_into_db(control_data, Check.__tablename__)

    def insert_thermometers():
        logger.info('inserting thermometers')
        thermometers = [
            Thermometer(
                device_id=thermometer.device_id,
                device_name=thermometer.device_name,
                device_group=thermometer.group
            ) for thermometer in read_all_thermometers()]
        clear_table(thermometer_table := Thermometer.__tablename__)
        insert_multiple_objects_into_db(thermometers, thermometer_table)

    clear_data_tables()
    insert_containers()
    insert_thermometers()


def read_relevant_temperature(task_id: str) -> list[Reading]:
    def relevant_thermometer_ids(the_container_id: str) -> list[str]:
        logger.info('fetching relevant thermometer ids')
        device_relationships = [
            ContainerThermometer(**val) for val in select_from_db(ContainerThermometer.__tablename__)]
        thermometer_ids = [rel.thermometer_id for rel in device_relationships if rel.container_id == the_container_id]
        return thermometer_ids

    def read_relevant_thermometers() -> list[Measure]:
        logger.info('reading relevant thermometer ids')
        relationships = [ContainerTask(**rel) for rel in select_from_db(ContainerTask.__tablename__)]
        container = [rel.container_id for rel in relationships if rel.task_id == task_id].pop()
        relevant_ids = relevant_thermometer_ids(container)
        return [t for t in read_all_thermometers() if t.device_id in relevant_ids]

    def insert_reads_into_db(insert_thermometers: list[Measure]) -> list[Reading]:
        logger.info('saving read temperatures')
        insert_thermometer_reads = [Reading(
            id=str(uuid4()),
            thermometer=t.device_id,
            temperature=t.temperature,
            read_time=t.measure_time,
            db_time=t.database_time)
            for t in insert_thermometers]
        insert_multiple_objects_into_db(insert_thermometer_reads, Reading.__tablename__)
        relation_data = [TaskRead(read_id=read.id, task_id=task_id) for read in insert_thermometer_reads]
        insert_multiple_objects_into_db(relation_data, TaskRead.__tablename__)
        return insert_thermometer_reads

    relevant_thermometers = read_relevant_thermometers()
    relevant_thermometer_reads = insert_reads_into_db(relevant_thermometers)
    return relevant_thermometer_reads


def create_checks_from_ctrls(check_ctrls: list[Ctrl]):
    logger.info('establishing check values')
    return [Check(
        id=str(uuid4()),
        timestamp=c.database_time,
        container=c.name,
        logged=c.logged,
        received=c.received,
        power=c.power,
        read_setpoint=c.setpoint
    ) for c in check_ctrls]


def create_and_save_checks(check_ctrls: list[Ctrl]) -> list[Check]:
    logger.info('saving check values')
    created_checks = create_checks_from_ctrls(check_ctrls)
    insert_multiple_objects_into_db(created_checks, Check.__tablename__)
    return created_checks


def create_and_save_control(control_temperature: str) -> Control:
    logger.info('saving control')
    control = Control(
        id=str(uuid4()),
        timestamp=int(time.time()),
        target_setpoint=control_temperature)
    insert_one_object_into_db(control, Control.__tablename__)
    return control


def set_process(set_id: str):
    def get_performed_set() -> Set:
        logger.info('fetching setting parameters for execution')
        return [Set(**s) for s in select_from_db(table_name=Set.__tablename__, where_equals={'id': set_id})].pop()

    def get_set_container_relationship() -> ContainerSet:
        logger.info('fetching target container')
        return [ContainerSet(**c) for c in select_from_db(
            table_name=ContainerSet.__tablename__, where_equals={'set_id': set_id})].pop()

    def create_set_control_pairing(performed_set_control: Control, related_set: Set):
        logger.info('pairing setting with created control')
        performed_control_relationship = SetControl(
            control_id=performed_set_control.id,
            set_id=related_set.id)
        insert_one_object_into_db(performed_control_relationship, SetControl.__tablename__)

    def end_set(finnish_set: Set):
        logger.info('ending setting')
        finnish_set.status = 'ended'
        update_status_in_db(finnish_set)

    def get_setting_control(all_controls: list[Ctrl], pairing: ContainerSet) -> Ctrl:
        logger.info('fetching working temperature setting value for comparison')
        return [c for c in all_controls if c.name == pairing.container_id].pop()

    def run_set(go_set: Set):
        logger.info('running setting of temperature')

        def driver_check_containers_and_execute_set(container_name: str, temp_setting: str) -> list[Ctrl]:
            logger.info(f'launching webdriver to set {temp_setting} in {container_name}')
            return ContainerSettingsDriver().check_containers_and_set_temperature(
                container=container_name,
                temperature=temp_setting)

        set_container_pairing = get_set_container_relationship()
        container_controls = driver_check_containers_and_execute_set(
            container_name=set_container_pairing.container_id,
            temp_setting=(set_temperature := f'{str(go_set.temperature)}.0'))
        create_and_save_checks(container_controls)
        performed_control = create_and_save_control(set_temperature)
        create_set_control_pairing(performed_control, go_set)
        setting_ctrl = get_setting_control(container_controls, set_container_pairing)
        if setting_ctrl.setpoint == set_temperature:
            end_set(go_set)

    performed_set = get_performed_set()
    logger.info(f'performed setting status: "{performed_set.status}"')

    if performed_set.status == 'running':
        run_set(performed_set)

    elif performed_set.status == 'cancelled':
        end_set(performed_set)


class InvalidSettingRetry(Exception):
    def __init__(self, message="Retried setting to no effect"):
        self.message = message
        super().__init__(self.message)


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
        logger.info(f'initiating driver to set {str(temperature_setting)}')
        driver_checks = driver_check_and_introduce_setting(
            container_name=task_container_name,
            temp_setting=(temperature_setting := f'{str(temperature_setting)}.0'))
        create_and_save_checks(driver_checks)
        performed_control = create_and_save_control(temperature_setting)
        create_task_control_pairing(performed_control, task_id)

    def end_task(ended_task: Task):
        logger.info('ending task')
        ended_task.status = 'ended'
        update_status_in_db(ended_task)

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
            if existing_check_temperature != running_task.t_start:
                begin_task()
            else:
                measured_maximum_temperatures = measure_temperature()
                preheat_check = any(r >= running_task.t_max for r in measured_maximum_temperatures)
                if preheat_check:
                    driver_set_go_save_checks_and_control(running_task.t_min + 1)

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
        except (InvalidSettingRetry, ExecuteButtonError) as ex:
            logging.warning(f'{ex}')
            error_task(running_task)


def check_containers():
    logging.info('driver checking containers')
    container_values_checked = ContainerValuesDriver().read_values()
    create_and_save_checks(container_values_checked)
