import time
from drive import ContainerValuesDriver, ContainerSettingsDriver
from measure import read_all_thermometers
from database import insert_multiple_objects_into_db, clear_table, select_from_db, update_status_in_db, \
    insert_one_object_into_db
from api import *
from uuid import uuid4


def initialize_database():
    def insert_containers():
        container_values_read = ContainerValuesDriver().read_values()
        containers = [Container(name=container.name) for container in container_values_read]
        clear_table(Check.__tablename__)
        clear_table(ContainerSet.__tablename__)
        clear_table(ContainerTask.__tablename__)
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
        clear_table(check_table := Check.__tablename__)
        insert_multiple_objects_into_db(control_data, check_table)

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


def read_relevant_temperature(task_id: str) -> list[Read]:
    def relevant_thermometer_ids(the_container_id: str) -> list[str]:
        device_relationships = [ContainerThermometer(**val) for val in select_from_db(ContainerThermometer.__tablename__)]
        thermometer_ids = [rel.thermometer_id for rel in device_relationships if rel.container_id == the_container_id]
        return thermometer_ids

    # tasks = [Task(**task) for task in select_from_db(Task.__tablename__)]
    # task = [task for task in tasks if task.id == task_id].pop()
    relationships = [ContainerTask(**rel) for rel in select_from_db(ContainerTask.__tablename__)]
    container = [rel.container_id for rel in relationships if rel.task_id == task_id].pop()
    relevant_ids = relevant_thermometer_ids(container)
    relevant_thermometers = [t for t in read_all_thermometers() if t.device_id in relevant_ids]

    relevant_thermometer_reads = [
        Read(
            id=str(uuid4()),
            thermometer=t.device_id,
            temperature=t.temperature,
            read_time=t.measure_time,
            db_time=t.database_time
        )
        for t in relevant_thermometers]

    insert_multiple_objects_into_db(relevant_thermometer_reads, Read.__tablename__)

    relation_data = [TaskReads(read_id=read.id, task_id=task_id) for read in relevant_thermometer_reads]
    insert_multiple_objects_into_db(relation_data, TaskReads.__tablename__)
    return relevant_thermometer_reads


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


def set_process(set_id: str):

    performed_set = [
        Set(**s) for s in select_from_db(
            table_name=Set.__tablename__, where_condition={'id': set_id})].pop()

    set_container = [
        ContainerSet(**c) for c in select_from_db(
            table_name=ContainerSet.__tablename__, where_condition={'set_id': set_id})].pop()

    if performed_set.status == 'cancelled':
        performed_set.status = 'ended'
        update_status_in_db(performed_set)

    if performed_set.status == 'running':
        setting_control = ContainerSettingsDriver().set_temperature(
            container=set_container.container_id,
            temperature=(set_temperature := f'{str(performed_set.temperature)}.0'))

        if setting_control.setpoint == set_temperature:
            performed_set.status = 'ended'
            update_status_in_db(performed_set)

            performed_control = Control(
                id=(control_id := str(uuid4())),
                timestamp=int(time.time()),
                target_setpoint=set_temperature
            )
            insert_one_object_into_db(performed_control, Control.__tablename__)

            performed_control_relationship = SetControl(
                control_id=control_id,
                set_id=performed_set.id
            )
            insert_one_object_into_db(performed_control_relationship, SetControl.__tablename__)


def task_process(task_id: str):

    performed_task = [
        Task(**s) for s in select_from_db(
            table_name=Task.__tablename__, where_condition={'id': task_id})].pop()

    task_container = [
        ContainerTask(**c) for c in select_from_db(
            table_name=ContainerTask.__tablename__, where_condition={'task_id': task_id})].pop()

    if performed_task.status == 'cancelled':
        performed_task.status = 'ended'
        update_status_in_db(performed_task)

    if performed_task.status == 'running':

        temperatures = [t.temperature for t in read_relevant_temperature(task_id)]

        print(task_container, temperatures)


