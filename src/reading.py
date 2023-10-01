from .measure import read_all_thermometers, Measure
from .database import insert_multiple_objects_into_db, select_from_db
from .api import ContainerThermometer, ContainerTask, Reading, TaskRead
from uuid import uuid4
import logging


logger = logging.getLogger()


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
