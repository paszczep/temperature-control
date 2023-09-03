import time
from drive import ContainerValuesDriver, ContainerSettingsDriver
from measure import read_all_thermometers
from database import insert_multiple_objects_into_db, clear_table, select_from_db, update_status_in_db
from api import *
from uuid import uuid4


def initialize_database():
    def insert_containers():
        containers = [Container(name=container.name) for container in ContainerValuesDriver().read_values()]
        clear_table(container_table := Container.__tablename__)
        insert_multiple_objects_into_db(containers, container_table)

    def insert_thermometers():
        thermometers = [
            Thermometer(
                device_id=thermometer.device_id,
                device_name=thermometer.device_name,
                device_group=thermometer.group
            ) for thermometer in read_all_thermometers()]
        clear_table(thermometer_table := Thermometer.__tablename__)
        insert_multiple_objects_into_db(thermometers, thermometer_table)

    insert_containers()
    insert_thermometers()


def relevant_thermometer_ids(the_container_id: str) -> list[str]:
    relationships = [ContainerThermometer(**val) for val in select_from_db(ContainerThermometer.__tablename__)]
    thermometer_ids = [rel.thermometer_id for rel in relationships if rel.container_id == the_container_id]
    return thermometer_ids


def read_temperature(task_id: int):
    tasks = [Task(**task) for task in select_from_db(Task.__tablename__)]
    task = [task for task in tasks if task.id == task_id].pop()
    relationships = [ContainerTask(**rel) for rel in select_from_db(ContainerTask.__tablename__)]
    container = [rel.container_id for rel in relationships if rel.task_id == task_id].pop()
    relevant_ids = relevant_thermometer_ids(container)
    relevant_measures = [measure for measure in read_all_thermometers() if measure.device_id in relevant_ids]

    reads = [
        Read(
            id=str(uuid4()),
            thermometer=measure.device_id,
            temperature=measure.temperature,
            read_time=measure.measure_time,
            db_time=measure.database_time
        )
        for measure in relevant_measures]

    insert_multiple_objects_into_db(reads, Read.__tablename__)

    relation_data = [TaskReads(read_id=read.id, task_id=task.id) for read in reads]
    insert_multiple_objects_into_db(relation_data, TaskReads.__tablename__)


def check_containers():
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
        for c in ContainerValuesDriver().read_values()]

    insert_multiple_objects_into_db(control_data, Check.__tablename__)


def temperature_setting_process(set_id: str):

    select_set = [
        Set(**s) for s in select_from_db(
            table_name=Set.__tablename__, where_condition={'id': set_id})].pop()

    set_container = [
        ContainerSet(**c) for c in select_from_db(
            table_name=ContainerSet.__tablename__, where_condition={'set_id': set_id})].pop()

    if select_set.status == 'cancelled':
        select_set.status = 'ended'
        update_status_in_db(select_set)

    if select_set.status == 'running':
        ContainerSettingsDriver().set_temperature(
            container=set_container.container_id,
            temperature=f'{str(select_set.temperature)}.0')

        time.sleep(5*60)

        select_set.status = 'ended'
        update_status_in_db(select_set)
