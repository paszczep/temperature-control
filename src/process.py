from .drive import ContainerValuesDriver, ContainerSettingsDriver, Ctrl
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

logging.basicConfig(
    stream=sys.stdout,
    level=logging.disable(),
    format='%(asctime)s: %(message)s'
)


def initialize_database():
    def clear_data_tables():
        logging.info('clearing data tables')
        for cleared_object in data_objects:
            clear_table(cleared_object.__tablename__)

    def insert_containers():
        logging.info('inserting containers')
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
        logging.info('inserting thermometers')
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
        logging.info('fetching relevant thermometer ids')
        device_relationships = [
            ContainerThermometer(**val) for val in select_from_db(ContainerThermometer.__tablename__)]
        thermometer_ids = [rel.thermometer_id for rel in device_relationships if rel.container_id == the_container_id]
        return thermometer_ids

    def read_relevant_thermometers() -> list[Measure]:
        logging.info('reading relevant thermometer ids')
        relationships = [ContainerTask(**rel) for rel in select_from_db(ContainerTask.__tablename__)]
        container = [rel.container_id for rel in relationships if rel.task_id == task_id].pop()
        relevant_ids = relevant_thermometer_ids(container)
        return [t for t in read_all_thermometers() if t.device_id in relevant_ids]

    def insert_reads_into_db(insert_thermometers: list[Measure]) -> list[Reading]:
        logging.info('saving read temperatures')
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
    logging.info('establishing check values')
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
    logging.info('saving check values')
    created_checks = create_checks_from_ctrls(check_ctrls)
    insert_multiple_objects_into_db(created_checks, Check.__tablename__)
    return created_checks


def create_and_save_control(control_temperature: str) -> Control:
    logging.info('saving control')
    control = Control(
        id=str(uuid4()),
        timestamp=int(time.time()),
        target_setpoint=control_temperature)
    insert_one_object_into_db(control, Control.__tablename__)
    return control


def set_process(set_id: str):
    def get_performed_set() -> Set:
        logging.info('fetching setting parameters for execution')
        return [Set(**s) for s in select_from_db(table_name=Set.__tablename__, where_equals={'id': set_id})].pop()

    def get_set_container_relationship() -> ContainerSet:
        logging.info('fetching target container')
        return [ContainerSet(**c) for c in select_from_db(
            table_name=ContainerSet.__tablename__, where_equals={'set_id': set_id})].pop()

    def create_set_control_pairing(performed_set_control: Control, related_set: Set):
        logging.info('pairing setting with created control')
        performed_control_relationship = SetControl(
            control_id=performed_set_control.id,
            set_id=related_set.id)
        insert_one_object_into_db(performed_control_relationship, SetControl.__tablename__)

    def end_set(finnish_set: Set):
        logging.info('ending setting')
        finnish_set.status = 'ended'
        update_status_in_db(finnish_set)

    def get_setting_control(all_controls: list[Ctrl], pairing: ContainerSet) -> Ctrl:
        logging.info('fetching working temperature setting value for comparison')
        return [c for c in all_controls if c.name == pairing.container_id].pop()

    def run_set(go_set: Set):
        logging.info('running setting of temperature')

        def driver_check_containers_and_execute_set(container_name: str, temp_setting: str) -> list[Ctrl]:
            logging.info(f'launching webdriver to set {temp_setting} in {container_name}')
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
    logging.info(f'performed setting status {performed_set.status}')

    if performed_set.status == 'running':
        run_set(performed_set)

    elif performed_set.status == 'cancelled':
        end_set(performed_set)


def task_process(task_id: str):
    logging.info('processing task')

    def driver_check_and_introduce_setting(container_name: str, temp_setting: str) -> list[Ctrl]:
        logging.info(f'launching webdriver to set {temp_setting} in {container_name}')
        return ContainerSettingsDriver().check_containers_and_set_temperature(
            container=container_name,
            temperature=temp_setting)

    def get_processed_task() -> Task:
        logging.info('fetching processed task')
        return [Task(**s) for s in select_from_db(
            table_name=Task.__tablename__, where_equals={'id': task_id})].pop()

    def end_task(ended_task: Task):
        logging.info('ending task')
        ended_task.status = 'ended'
        update_status_in_db(ended_task)

    def retrieve_which_controls() -> list[str]:
        logging.info('establishing relevant controls')
        return select_from_db(table_name=TaskControl.__tablename__,
                              columns=['control_id'],
                              where_equals={'task_id': task_id},
                              return_keys=False)

    def retrieve_relevant_controls(control_ids: list) -> list[Control]:
        logging.info('retrieving relevant controls')
        return [Control(**control) for control in
                select_from_db(Control.__tablename__, where_in={'id': control_ids}, return_keys=True)]

    def driver_set_go_save_checks_and_control(temperature_setting: int):
        logging.info(f'initiating driver to set {str(temperature_setting)}')
        driver_checks = driver_check_and_introduce_setting(
            container_name=task_container_name,
            temp_setting=(temperature_setting := f'{str(temperature_setting)}.0'))
        create_and_save_checks(driver_checks)
        create_and_save_control(temperature_setting)

    def get_related_container() -> ContainerTask:
        logging.info('fetching processed container')
        return [ContainerTask(**c) for c in select_from_db(
            table_name=ContainerTask.__tablename__, where_equals={'task_id': task_id})].pop()

    def is_younger_than(age_timestamp: int, minutes: int = 15) -> bool:
        return bool(age_timestamp > (time.time() - 60*minutes))

    def retrieve_container_check(checked_container_id: str) -> Union[Check, None]:
        if (select_checks := select_from_db(
                            table_name=Check.__tablename__,
                            where_equals={'container': checked_container_id},
                            return_keys=True)):
            existing_check = [
                (checking := Check(**check)) for check in select_checks if is_younger_than(checking.timestamp)]
            return existing_check.pop() if existing_check else None

    def begin_task():
        return driver_set_go_save_checks_and_control(temperature_setting=performed_task.t_start)

    def retrieve_relevant_reads() -> list[Reading]:
        what_reads = select_from_db(
            TaskRead.__tablename__, ['read_id'], where_equals={'task_id': task_id}, return_keys=False)
        return [use_read(Reading(**r)) for r in
                select_from_db(Reading.__tablename__, where_in={"read_id": what_reads}, return_keys=True)]

    def measure_relevant_reads() -> list[Reading]:
        read_all = [use_read(r) for r in read_relevant_temperature(task_id)]
        read_valid = [r for r in read_all if is_younger_than(r.read_time)]
        return read_valid

    def get_recent_controlled_setting(retrieved_controls: list[Control]) -> Decimal:
        recent_timestamp = max(c.timestamp for c in retrieved_controls)
        recent_controlled_setting = [
            c.target_setpoint for c in retrieved_controls if c.timestamp == recent_timestamp].pop()
        return Decimal(recent_controlled_setting)

    def measure_temperature_and_decide(existing_check: Check):
        what_control_ids = retrieve_which_controls()
        if not what_control_ids:
            begin_task()

        retrieved_controls = retrieve_relevant_controls(what_control_ids)
        recent_setting = get_recent_controlled_setting(retrieved_controls)

        retrieved_reads = retrieve_relevant_reads()
        measured_reads = measure_relevant_reads()
        all_temperatures = [t.temperature for t in measured_reads + retrieved_reads]

        return existing_check, task_container_name, all_temperatures, performed_task, retrieved_controls, retrieved_reads

    performed_task = get_processed_task()
    task_container_name = get_related_container().container_id

    if performed_task.status == 'cancelled':
        end_task(performed_task)

    if performed_task.status == 'running':

        container_check = retrieve_container_check(task_container_name)

        if not container_check and is_younger_than(performed_task.start):
            begin_task()
        elif container_check:
            measure_temperature_and_decide(container_check)


def check_containers():
    logging.info('driver checking containers')
    container_values_checked = ContainerValuesDriver().read_values()
    create_and_save_checks(container_values_checked)
