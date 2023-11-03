from src.external_apis.measure import read_all_thermometers, DeviceRead
from src.internal_apis.database_query import insert_multiple_objects_into_db, select_from_db
from src.internal_apis.models_data import ContainerThermometer, ContainerTask, Reading, TaskRead, use_read
from uuid import uuid4
import logging
from decimal import Decimal


def task_relevant_temperature_reading(task_id: str) -> list[Reading]:
    logging.info('reading relevant temperature')

    def relevant_thermometer_ids(the_container_id: str) -> list[str]:
        logging.info('fetching container thermometer connections')
        device_relationships = [
            ContainerThermometer(**val) for val in select_from_db(ContainerThermometer.__tablename__)]
        thermometer_ids = [rel.thermometer_id for rel in device_relationships if rel.container_id == the_container_id]
        logging.info(f'relevant thermometers found {len(thermometer_ids)}')
        return thermometer_ids

    def read_relevant_thermometers() -> list[DeviceRead]:
        logging.info('reading relevant thermometer ids')
        relationships = [ContainerTask(**rel) for rel in select_from_db(ContainerTask.__tablename__)]
        container = [rel.container_id for rel in relationships if rel.task_id == task_id].pop()
        relevant_ids = relevant_thermometer_ids(container)
        relevant_reads = [t for t in read_all_thermometers() if t.device_id in relevant_ids]
        logging.info(f'relevant device reads {len(relevant_reads)}')
        return relevant_reads

    def insert_reads_into_db(insert_measurements: list[DeviceRead]) -> list[Reading]:
        logging.info(f'saving read temperatures {len(insert_measurements)}')
        insert_thermometer_reads = [Reading(
                id=str(uuid4()),
                thermometer=t.device_id,
                temperature=t.temperature,
                read_time=t.measure_time,
                db_time=t.database_time)
            for t in insert_measurements]
        insert_multiple_objects_into_db(insert_thermometer_reads)
        relation_data = [TaskRead(read_id=read.id, task_id=task_id) for read in insert_thermometer_reads]
        insert_multiple_objects_into_db(relation_data)
        logging.info(f'db inserted device reads {len(insert_thermometer_reads)}')
        return insert_thermometer_reads

    relevant_thermometers = read_relevant_thermometers()
    relevant_thermometer_reads = insert_reads_into_db(relevant_thermometers)
    logging.info(f'relevant thermometer reads {len(relevant_thermometer_reads)} ')
    return relevant_thermometer_reads


def measure_timely_temperature(task_id: str) -> list[Decimal]:
    logging.info('measuring temperature')

    def measure_all_temperature() -> list[Reading]:
        logging.info('read all temperature')
        all_reads = [use_read(r) for r in task_relevant_temperature_reading(task_id)]
        logging.info(f'thermometer reads {len(all_reads)}')
        for log_read in all_reads:
            logging.info(f'{log_read.get_log_info()}')
        return all_reads

    def time_valid_reads():
        read_time_valid = [r.temperature for r in read_all if r.is_younger_than()]
        logging.info(f'{len(read_time_valid)} valid temperature reads: '
                     f'{", ".join(str(log_read) for log_read in read_time_valid)}')
        return read_time_valid

    read_all = measure_all_temperature()
    read_valid = time_valid_reads()
    return read_valid


def retrieve_past_reads(task_id: str):
    relevant_read_ids = select_from_db(
        TaskRead.__tablename__,
        columns=['read_id'],
        where_equals={'task_id': task_id},
        keys=False)
    relevant_read_records = select_from_db(Reading.__tablename__, where_in={'id': relevant_read_ids})
    relevant_reads = [use_read(Reading(**r)) for r in relevant_read_records]
    logging.info(f'past reads {len(relevant_reads)}')
    return relevant_reads


def retrieve_past_read_temperatures(task_id: str) -> list[Decimal]:
    return [r.temperature for r in retrieve_past_reads(task_id)]
