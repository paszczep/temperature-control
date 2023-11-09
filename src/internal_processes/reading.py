from src.external_apis.measure import read_all_thermometers, DeviceRead
from src.internal_apis.database_query import insert_multiple_objects_into_db, select_from_db
from src.internal_apis.models_data import ContainerThermometerPair, ReadingValues, TaskReadPair, \
    use_read
from uuid import uuid4
from logging import info
from decimal import Decimal
from typing import Union


class ReadingTasking:
    task_id: str
    container_name: str
    current_reads: list[ReadingValues]
    past_reads: Union[None, list[ReadingValues]]
    current_temperatures: list[Decimal]
    past_temperatures: Union[None, list[Decimal]]

    def task_relevant_temperature_reading(self) -> list[ReadingValues]:
        info('reading relevant temperature')

        def relevant_thermometer_ids() -> list[str]:
            info('fetching container thermometer pairs')
            device_pairings = [
                ContainerThermometerPair(**val) for val in select_from_db(ContainerThermometerPair.__tablename__)]
            thermometer_ids = [rel.thermometer_id for rel in device_pairings if rel.container_id == self.container_name]
            info(f'relevant thermometers found {len(thermometer_ids)}')
            return thermometer_ids

        def read_relevant_thermometers() -> list[DeviceRead]:
            info('reading relevant thermometer ids')
            relevant_ids = relevant_thermometer_ids()
            relevant_reads = [t for t in read_all_thermometers() if t.device_id in relevant_ids]
            info(f'relevant device reads {len(relevant_reads)}')
            return relevant_reads

        def insert_reads_into_db(insert_measurements: list[DeviceRead]) -> list[ReadingValues]:
            info(f'saving read temperatures {len(insert_measurements)}')
            insert_thermometer_reads = [ReadingValues(
                id=str(uuid4()),
                thermometer=t.device_id,
                temperature=t.temperature,
                read_time=t.measure_time,
                db_time=t.database_time)
                for t in insert_measurements]
            insert_multiple_objects_into_db(insert_thermometer_reads)
            relation_data = [TaskReadPair(read_id=read.id, task_id=self.task_id) for read in insert_thermometer_reads]
            insert_multiple_objects_into_db(relation_data)
            info(f'db inserted device reads {len(insert_thermometer_reads)}')
            return insert_thermometer_reads

        relevant_thermometers = read_relevant_thermometers()
        relevant_thermometer_reads = insert_reads_into_db(relevant_thermometers)
        info(f'relevant thermometer reads {len(relevant_thermometer_reads)} ')
        return relevant_thermometer_reads

    def measure_timely_temperature(self) -> list[Decimal]:
        info('measuring temperature')

        def measure_all_temperature() -> list[ReadingValues]:
            info('read all temperature')
            all_reads = [use_read(r) for r in self.task_relevant_temperature_reading()]
            info(f'thermometer reads {len(all_reads)}')
            for log_read in all_reads:
                info(f'{log_read.get_log_info()}')
            return all_reads

        def time_valid_reads():
            read_time_valid = [r.temperature for r in read_all if r.is_younger_than()]
            info(f'{len(read_time_valid)} time valid temperature reads: '
                 f'{", ".join(str(log_read) for log_read in read_time_valid)}')
            return read_time_valid

        read_all = measure_all_temperature()
        read_valid = time_valid_reads()
        return read_valid

    def retrieve_past_reads(self):
        relevant_read_ids = select_from_db(
            TaskReadPair.__tablename__,
            columns=['read_id'],
            where_equals={'task_id': self.task_id},
            keys=False)
        relevant_read_records = select_from_db(ReadingValues.__tablename__, where_in={'id': relevant_read_ids})
        relevant_reads = [use_read(ReadingValues(**r)) for r in relevant_read_records]
        info(f'past reads {len(relevant_reads)}')
        return relevant_reads

    def __init__(self, task_id: str, container: str):
        self.task_id = task_id
        self.container_name = container
        self.past_reads = self.retrieve_past_reads()
        self.current_reads = self.task_relevant_temperature_reading()
        self.current_temperatures = [r.temperature for r in self.current_reads]
        self.past_temperatures = [r.temperature for r in self.past_reads]
