from src.external_apis.drive_control import CheckContainersDriver
from src.external_apis.measure import read_all_thermometers
from src.internal_apis.database_query import insert_multiple_objects_into_db, clear_table
from src.internal_apis.models import ThingContainer, ValuesCheck, ThingThermometer, data_objects
from uuid import uuid4
from logging import info


def initialize_database():

    def insert_containers():
        info('init inserting containers')
        container_values_read = CheckContainersDriver().read_values()
        containers = [ThingContainer(name=container.name) for container in container_values_read]
        insert_multiple_objects_into_db(containers)

        check_data = [
            ValuesCheck(
                id=str(uuid4()),
                timestamp=c.database_time,
                container=c.name,
                logged=c.logged,
                received=c.received,
                power=c.power,
                read_setpoint=c.setpoint
            )
            for c in container_values_read]
        insert_multiple_objects_into_db(check_data)

    def insert_thermometers():
        info('init inserting thermometers')
        thermometers = [
            ThingThermometer(
                device_id=thermometer.device_id,
                device_name=thermometer.device_name,
                device_group=thermometer.group
            ) for thermometer in read_all_thermometers()]
        insert_multiple_objects_into_db(thermometers)

    def clear_data_tables():
        info('init clear data tables')
        for cleared_object in data_objects:
            clear_table(cleared_object.__tablename__)

    clear_data_tables()
    insert_containers()
    insert_thermometers()

