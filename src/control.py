from drive import ContainerValuesDriver
from measure import read_all_thermometers
from database import insert_multiple_objects_into_db, clear_table, select_from_db
from api import *


def initialize_database():
    containers = [Container(name=container.name) for container in ContainerValuesDriver().read_values()]
    clear_table(container_table := Container.__tablename__)
    insert_multiple_objects_into_db(containers, container_table)
    thermometers = [
        Meter(
            device_id=thermometer.device_id,
            device_name=thermometer.device_name
        ) for thermometer in read_all_thermometers()]
    clear_table(thermometer_table := Meter.__tablename__)
    insert_multiple_objects_into_db(thermometers, thermometer_table)


def relevant_thermometer_ids(the_container_id: str) -> list[int]:
    relationships = [ContainerMeter(**val) for val in select_from_db(ContainerMeter.__tablename__)]
    thermometer_ids = [rel.thermometer_id for rel in relationships if rel.container_id == the_container_id]
    return thermometer_ids


def read_temperature(task_id: int):
    tasks = [Task(**task) for task in select_from_db(Task.__tablename__)]
    task = [task for task in tasks if task.id == task_id].pop()
    relationships = [ContainerTask(**rel) for rel in select_from_db(ContainerTask.__tablename__)]
    container = [rel.container_id for rel in relationships if rel.task_id == task_id].pop()
    relevant_ids = relevant_thermometer_ids(container)
    relevant_measures = [measure for measure in read_all_thermometers() if measure.device_id in relevant_ids]
    existing_read_ids = select_from_db(Read.__tablename__, columns=['id'], keys=False)
    if not existing_read_ids:
        existing_read_ids = [0]
    select_id = max(existing_read_ids)

    reads = [Read(
        id=(select_id := select_id + 1),
        thermometer=measure.device_id,
        temperature=measure.temperature,
        read_time=measure.measure_time,
        db_time=measure.database_time
    ) for measure in relevant_measures]
    insert_multiple_objects_into_db(reads, Read.__tablename__)

    relation_data = [TaskReads(read_id=read.id, task_id=task.id) for read in reads]
    insert_multiple_objects_into_db(relation_data, TaskReads.__tablename__)


if __name__ == "__main__":
    read_temperature()
