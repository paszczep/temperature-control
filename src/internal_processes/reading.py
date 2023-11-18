from src.external_apis.measure import read_all_thermometers, DeviceRead
from src.internal_apis.database_query import insert_multiple_objects_into_db, select_from_db
from src.internal_apis.models import PairContainerThermometer, ValuesReading, PairTaskRead, use_read
from uuid import uuid4
from logging import info
from decimal import Decimal
from typing import Union


class ReadingTasking:
    _task_id: str
    _container_name: str
    relevant_reads: list[ValuesReading]
    past_reads: Union[None, list[ValuesReading]]
    current_temperatures: list[Decimal]
    past_temperatures: Union[None, list[Decimal]]

    def relevant_thermometer_ids(self) -> list[str]:
        info('read fetching container thermometer pairs')
        device_pairings = [
            PairContainerThermometer(**val) for val in select_from_db(PairContainerThermometer.__tablename__)]
        thermometer_ids = [rel.thermometer_id for rel in device_pairings if rel.container_id == self._container_name]
        info(f'read relevant thermometer ids found {len(thermometer_ids)}')
        return thermometer_ids

    def read_relevant_thermometers(self) -> list[DeviceRead]:
        info('read relevant thermometers')
        relevant_ids = self.relevant_thermometer_ids()
        relevant_reads = [t for t in read_all_thermometers() if t.device_id in relevant_ids]
        info(f'read relevant count {len(relevant_reads)}')
        if relevant_reads:
            temperatures = ', '.join(r.temperature for r in relevant_reads)
            info(f'read temperatures: {temperatures}')
        return relevant_reads

    def create_and_insert_reads(self, insert_measurements: list[DeviceRead]) -> list[ValuesReading]:
        info(f'read saving temperatures {len(insert_measurements)}')
        insert_thermometer_reads = [ValuesReading(
            id=str(uuid4()),
            thermometer=t.device_id,
            temperature=t.temperature,
            read_time=t.measure_time,
            db_time=t.database_time)
            for t in insert_measurements]
        insert_multiple_objects_into_db(insert_thermometer_reads)
        relation_data = [PairTaskRead(read_id=read.id, task_id=self._task_id) for read in insert_thermometer_reads]
        insert_multiple_objects_into_db(relation_data)
        info(f'read inserted into db count: {len(insert_thermometer_reads)}')
        return insert_thermometer_reads

    def task_relevant_temperature_reading(self) -> list[ValuesReading]:
        info('read relevant temperature')
        relevant_thermometers = self.read_relevant_thermometers()
        relevant_thermometer_reads = self.create_and_insert_reads(relevant_thermometers)
        info(f'read container thermometer count: {len(relevant_thermometer_reads)}')
        relevant_thermometer_reads = [use_read(r) for r in relevant_thermometer_reads]
        return relevant_thermometer_reads

    def time_valid_reads(self) -> list[Decimal]:
        read_time_valid = [r.temperature for r in self.relevant_reads if r.is_recent()]
        info(f'read time valid count: {len(read_time_valid)}')
        return read_time_valid

    def retrieve_past_reads(self) -> Union[None, list[ValuesReading]]:
        relevant_read_ids = select_from_db(
            PairTaskRead.__tablename__,
            columns=['read_id'],
            where_equals={'task_id': self._task_id},
            keys=False)
        if relevant_read_ids:
            relevant_read_records = select_from_db(ValuesReading.__tablename__, where_in={'id': relevant_read_ids})
            relevant_reads = [use_read(ValuesReading(**r)) for r in relevant_read_records]
            info(f'reads past count: {len(relevant_reads)}')
            return relevant_reads
        else:
            return None

    def __init__(self, task_id: str, container: str):
        info('read initiate')
        self._task_id = task_id
        self._container_name = container
        self.past_reads = self.retrieve_past_reads()
        if self.past_reads:
            self.past_temperatures = [r.temperature for r in self.past_reads]
        self.relevant_reads = self.task_relevant_temperature_reading()
        self.current_temperatures = self.time_valid_reads()

    def measure_all_temperature(self) -> list[ValuesReading]:
        info('read all temperature')
        all_reads = [use_read(r) for r in self.task_relevant_temperature_reading()]
        info(f'read thermometer all count: {len(all_reads)}')
        for log_read in all_reads:
            info(f'{log_read.get_log_info()}')
        return all_reads
