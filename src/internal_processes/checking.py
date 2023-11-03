from src.external_apis.drive import ContainerValuesDriver, Ctrl
from src.internal_apis.database_query import (insert_multiple_objects_into_db, select_from_db)
from src.internal_apis.models_data import Check, ContainerTask
from uuid import uuid4
from decimal import Decimal
from typing import Union
import logging

logger = logging.getLogger()


def get_related_container_name(task_id: str) -> str:
    return [ContainerTask(**c) for c in select_from_db(
        table_name=ContainerTask.__tablename__, where_equals={'task_id': task_id})].pop().container_id


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
    insert_multiple_objects_into_db(created_checks)
    return created_checks


def check_containers():
    logging.info('driver checking containers')
    container_values_checked = ContainerValuesDriver().read_values()
    create_and_save_checks(container_values_checked)


def retrieve_relevant_checks(checked_container_id: str) -> Union[None, list[Check]]:
    logger.info('retrieving check temperature')
    select_checks = select_from_db(
        table_name=Check.__tablename__,
        where_equals={'container': checked_container_id},
        keys=True)
    logger.info(f'selected checks {len(select_checks)}')
    if select_checks:
        all_checks = [Check(**check) for check in select_checks]
        for check in all_checks:
            logger.info(f'existing checks {check.get_log_info()}')
        return all_checks
    else:
        return None


def retrieve_recent_check_temperature(checked_container_id: str) -> Union[Decimal, None]:
    logger.info('retrieving check temperature')
    all_checks = retrieve_relevant_checks(checked_container_id)
    if all_checks:
        max_check_timestamp = max(c.timestamp for c in all_checks)
        existing_check = [check for check in all_checks if check.timestamp == max_check_timestamp].pop()
        logger.info(f'existing check {existing_check.get_log_info()}')
        if existing_check.is_younger_than(minutes=60):
            logger.info(f'existing check temperature {existing_check.read_setpoint}')
            return Decimal(existing_check.read_setpoint)
