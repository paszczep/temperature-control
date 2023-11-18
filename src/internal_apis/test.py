from src.internal_apis.database_connect import db_connection_and_cursor
from src.external_apis.measure import read_all_thermometers, DeviceRead
from src.internal_apis.database_query import select_from_db
from src.internal_apis.models import ThingContainer, ThingThermometer
from psycopg2.extensions import cursor, connection
from logging import info


class Test:
    _containers: list[ThingContainer]
    _thermometers: list[ThingThermometer]

    def test_database_connection(self):
        info('testing database connection and cursor')
        db_connection, db_cursor = db_connection_and_cursor()
        assert isinstance(db_connection, connection)
        assert isinstance(db_cursor, cursor)

    def retrieve_things(self):
        self._containers = [ThingContainer(**c) for c in select_from_db(ThingContainer.__tablename__)]
        self._thermometers = [ThingThermometer(**t) for t in select_from_db(ThingThermometer.__tablename__)]
        info(f'containers: {len(self._containers)}')
        if self._containers:
            for container in self._containers:
                info(f'   {container.name} {container.label}')
        info(f'thermometers: {len(self._thermometers)}')
        if self._thermometers:
            for thermometer in self._thermometers:
                info(f'   {thermometer.device_name} {thermometer.device_group}')

    def test_things(self):
        info('testing availability of things')
        self.retrieve_things()
        assert len(self._containers) > 0
        assert isinstance(self._containers.pop(), ThingContainer)
        assert len(self._thermometers) > 0
        assert isinstance(self._thermometers.pop(), ThingThermometer)

    def test_measurement(self):
        info('testing measurement availability')
        read_thermometers = read_all_thermometers()
        for device_log in read_thermometers:
            info(f'   {device_log.measure_time}   '
                 f'{device_log.device_name}   '
                 f'{device_log.temperature}')
        assert len(read_thermometers) > 0
        assert isinstance(read_thermometers.pop(), DeviceRead)


def perform_test():
    test = Test()
    test.test_database_connection()
    test.test_things()
    test.test_measurement()
