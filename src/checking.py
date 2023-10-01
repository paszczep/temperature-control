from .drive import ContainerValuesDriver, Ctrl
from .database import insert_multiple_objects_into_db, insert_one_object_into_db
from .api import Check, Control
from uuid import uuid4
import logging
import time

logger = logging.getLogger()


class InvalidSettingRetry(Exception):
    def __init__(self, message="Retried setting to no effect"):
        self.message = message
        super().__init__(self.message)


def create_and_save_checks(check_ctrls: list[Ctrl]) -> list[Check]:
    logger.info('saving check values')

    def create_checks_from_ctrls(source_ctrls: list[Ctrl]):
        return [Check(
            id=str(uuid4()),
            timestamp=c.database_time,
            container=c.name,
            logged=c.logged,
            received=c.received,
            power=c.power,
            read_setpoint=c.setpoint
        ) for c in source_ctrls]
    created_checks = create_checks_from_ctrls(check_ctrls)
    insert_multiple_objects_into_db(created_checks, Check.__tablename__)
    return created_checks


def create_and_save_control(control_temperature: str) -> Control:
    logger.info('saving control')
    control = Control(
        id=str(uuid4()),
        timestamp=int(time.time()),
        target_setpoint=control_temperature)
    insert_one_object_into_db(control, Control.__tablename__)
    return control


def check_containers():
    logging.info('driver checking containers')
    container_values_checked = ContainerValuesDriver().read_values()
    create_and_save_checks(container_values_checked)
