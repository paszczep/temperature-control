from src.external_apis.measure import read_all_thermometers, Measure
from src.internal_apis.database import insert_multiple_objects_into_db, select_from_db
from src.internal_apis.models import ContainerThermometer, ContainerTask, Reading, TaskRead, use_read, is_younger_than
from uuid import uuid4
import logging
from decimal import Decimal

logger = logging.getLogger()


def read_relevant_temperature(task_id: str) -> list[Reading]:
    logger.info('reading relevant temperature')

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


def measure_all_temperature(task_id: str) -> list[Reading]:
    logger.info('read all temperature')
    read_all = [use_read(r) for r in read_relevant_temperature(task_id)]
    logger.info(f'all thermometer reads {len(read_all)}:')
    for log_all_read in read_all:
        logger.info(f'{log_all_read.get_log_info()}')
    return read_all


def measure_timely_temperature(task_id: str) -> list[Decimal]:
    logger.info('measuring temperature')
    read_all = measure_all_temperature(task_id)
    read_valid = [r.temperature for r in read_all if is_younger_than(r.read_time)]
    logger.info(f'valid thermometer reads {len(read_valid)}')
    for log_read in read_valid:
        logger.info(f'valid temperature read {log_read}')
    return read_valid
