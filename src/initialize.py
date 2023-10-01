from .drive import ContainerValuesDriver
from .measure import read_all_thermometers
from .database import insert_multiple_objects_into_db, clear_table
from .api import Container, Check, Thermometer, data_objects
from uuid import uuid4
import logging


logger = logging.getLogger()


def initialize_database():
    def clear_data_tables():
        logger.info('clearing data tables')
        for cleared_object in data_objects:
            clear_table(cleared_object.__tablename__)

    def insert_containers():
        logger.info('inserting containers')
        container_values_read = ContainerValuesDriver().read_values()
        containers = [Container(name=container.name) for container in container_values_read]
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
        insert_multiple_objects_into_db(control_data, Check.__tablename__)

    def insert_thermometers():
        logger.info('inserting thermometers')
        thermometers = [
            Thermometer(
                device_id=thermometer.device_id,
                device_name=thermometer.device_name,
                device_group=thermometer.group
            ) for thermometer in read_all_thermometers()]
        clear_table(thermometer_table := Thermometer.__tablename__)
        insert_multiple_objects_into_db(thermometers, thermometer_table)

    clear_data_tables()
    insert_containers()
    insert_thermometers()
