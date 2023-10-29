from src.external_apis.drive import Ctrl
from src.internal_apis.database_query import select_from_db, update_status_in_db, insert_one_object_into_db
from src.internal_apis.models import Control, ContainerSet, Setting, SetControl
from src.internal_processes.checking import create_and_save_checks
from src.internal_processes.controlling import create_and_save_control, create_set_control_pairing
from src.internal_processes.driving import driver_check_and_introduce_setting

import logging

logger = logging.getLogger()


def get_set_container_relationship(set_id: str) -> ContainerSet:
    logger.info('fetching target container')
    return [ContainerSet(**c) for c in select_from_db(
        table_name=ContainerSet.__tablename__, where_equals={'set_id': set_id})].pop()


def set_process(set_id: str):
    def get_performed_set() -> Setting:
        logger.info('fetching setting parameters for execution')
        select_sets = select_from_db(table_name=Setting.__tablename__, where_equals={'id': set_id})
        if select_sets:
            return [Setting(**s) for s in select_sets].pop()
        else:
            logger.info('setting task no longer exists')
            exit()

    def end_set(finnish_set: Setting):
        logger.info('ending setting')
        finnish_set.status = 'ended'
        update_status_in_db(finnish_set)

    def get_setting_control(all_controls: list[Ctrl], pairing: ContainerSet) -> Ctrl:
        logger.info('fetching working temperature setting value for comparison')
        return [c for c in all_controls if c.name == pairing.container_id].pop()

    def run_set(go_set: Setting):
        def execute_setting_driver():
            logger.info('running setting of temperature')
            return driver_check_and_introduce_setting(
                container_name=set_container_pairing.container_id,
                temp_setting=set_temperature)

        set_container_pairing = get_set_container_relationship(set_id)
        set_temperature = f'{str(go_set.temperature)}.0'
        container_controls = execute_setting_driver()
        create_and_save_checks(container_controls)
        performed_control = create_and_save_control(set_temperature)
        create_set_control_pairing(performed_control, go_set)
        setting_ctrl = get_setting_control(container_controls, set_container_pairing)
        if setting_ctrl.setpoint == set_temperature:
            end_set(go_set)

    performed_set = get_performed_set()
    logger.info(f'performed setting status: "{performed_set.status}"')

    if performed_set.status == 'running':
        run_set(performed_set)
